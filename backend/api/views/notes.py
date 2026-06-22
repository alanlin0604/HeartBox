"""Mood notes, tags, attachments, sharing, import/export endpoints.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import csv
import io
import mimetypes
import threading
from datetime import datetime

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone

from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    CounselorProfile, MoodNote, NoteAttachment, SharedNote, Tag,
)
from ..serializers import (
    MoodNoteListSerializer, MoodNoteSerializer, NoteAttachmentSerializer,
    SharedNoteSerializer, TagSerializer,
)
from ..services.audit import log_action
from ..services.pdf_export import generate_notes_pdf
from ..services.search import search_notes
from ..throttles import (
    ExportThrottle, GeneralWriteThrottle, NoteCreateThrottle, UploadThrottle,
)

from . import (
    MAX_BATCH_DELETE, MAX_EXPORT_NOTES, User, create_notification_if_enabled,
    error_response, logger,
)


def _ai_analysis_worker(note_id, user_id):
    """Background worker that runs the AI analysis pipeline and pushes
    the resulting sentiment/stress/feedback to the user over WebSocket.

    Module-level (not bound to a class) so threading.Thread can call it
    without keeping a reference to a ViewSet instance — that instance is
    request-scoped and may be discarded by the time the thread runs.

    Wraps the entire pipeline in a try/except: under no circumstance do
    we want a background thread to crash the worker process. The AI
    engine itself has three tiers of fallback (OpenAI+RAG → OpenAI plain
    → local keyword), so an analysis failure here is a last-resort.
    """
    try:
        from api.models import MoodNote
        from api.services.ai_engine import ai_engine

        try:
            note = MoodNote.objects.get(id=note_id, is_deleted=False)
        except MoodNote.DoesNotExist:
            return
        if not note.content:
            return

        result = ai_engine.analyze(note.content)
        note.sentiment_score = result['sentiment_score']
        note.stress_index = result['stress_index']
        note.ai_feedback = result['ai_feedback']
        note.save(update_fields=['sentiment_score', 'stress_index', 'ai_feedback'])

        # Push the result to the user's notification WebSocket channel so
        # the active client can refresh the note in-place. Wrapped in try
        # because: layer may be None when channels isn't configured (dev
        # SQLite-only path), the user might be offline, or the group key
        # may not exist yet. Either way the DB row is already updated, so
        # the next time the user opens the note they'll see the analysis.
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            layer = get_channel_layer()
            logger.info('WS_FANOUT_START note=%s user=%s layer=%s', note.id, user_id, type(layer).__name__ if layer else None)
            if layer is not None:
                async_to_sync(layer.group_send)(
                    f'notifications_{user_id}',
                    {
                        'type': 'notify',
                        'data': {
                            'type': 'note_analyzed',
                            'data': {
                                'note_id': note.id,
                                'sentiment_score': note.sentiment_score,
                                'stress_index': note.stress_index,
                                'ai_feedback': note.ai_feedback,
                            },
                        },
                    },
                )
                logger.info('WS_FANOUT_OK note=%s user=%s group=notifications_%s', note.id, user_id, user_id)
        except Exception:
            logger.exception('WS_FANOUT_FAIL after AI analysis')
    except Exception:
        logger.exception('Background AI analysis worker crashed for note %s', note_id)


def _post_save_worker(user_id):
    """Run achievement checks after a note is saved.

    Previously this ran inline in perform_create, but check_achievements
    fires ~25 aggregate queries against MoodNote / SharedNote / Booking /
    AIChatSession / Conversation / Message / Feedback / NoteAttachment /
    Friendship / SharedWithFriend / FriendComment / PublicPost /
    PostReaction / DailySleep / HealthMetric / Habit / SelfAssessment /
    WellnessSession / DashboardLayout — and a two-pass loop reruns the
    whole thing if any meta achievement unlocks. On Neon, with a user
    that has 800+ notes (the seed_demo_account default), each pass takes
    1-2 seconds; the total cost was driving the user-perceived save
    latency to 5+ seconds even though AI analysis was already async.

    Unlock notifications still reach the frontend via the WebSocket
    fan-out inside `_emit_unlock_notifications`, so dropping the
    X-New-Achievements response header (which carried the same info on
    the synchronous path) is a non-regression.
    """
    try:
        from django.contrib.auth import get_user_model
        from api.services.achievements import check_achievements
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            return
        check_achievements(user)
    except Exception:
        logger.exception('Background achievement check failed for user %s', user_id)


def _vision_analysis_worker(note_id, user_id, image_urls):
    """Background worker for image-aware re-analysis. Same shape as the
    text-only worker but calls analyze_with_images on the vision provider
    (LLaVA via the local llm_server)."""
    try:
        from api.models import MoodNote
        from api.services.ai_engine import ai_engine

        try:
            note = MoodNote.objects.get(id=note_id, is_deleted=False)
        except MoodNote.DoesNotExist:
            return
        if not note.content or not image_urls:
            return

        result = ai_engine.analyze_with_images(note.content, image_urls)
        note.sentiment_score = result['sentiment_score']
        note.stress_index = result['stress_index']
        note.ai_feedback = result['ai_feedback']
        note.save(update_fields=['sentiment_score', 'stress_index', 'ai_feedback'])

        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            layer = get_channel_layer()
            if layer is not None:
                async_to_sync(layer.group_send)(
                    f'notifications_{user_id}',
                    {
                        'type': 'notify',
                        'data': {
                            'type': 'note_analyzed',
                            'data': {
                                'note_id': note.id,
                                'sentiment_score': note.sentiment_score,
                                'stress_index': note.stress_index,
                                'ai_feedback': note.ai_feedback,
                                'with_images': True,
                            },
                        },
                    },
                )
        except Exception:
            logger.exception('WebSocket fan-out failed after vision analysis')
    except Exception:
        logger.exception('Background vision analysis worker crashed for note %s', note_id)


class TagViewSet(viewsets.ModelViewSet):
    """CRUD operations for user tags."""
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Tag.objects.none()
        return Tag.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def cloud(self, request):
        """Tag cloud with usage counts. Returns [{name, count, color}]."""
        tags = self.get_queryset().annotate(
            count=Count('notes', filter=Q(notes__is_deleted=False))
        ).filter(count__gt=0).order_by('-count')[:20]
        return Response([
            {'name': tag.name, 'count': tag.count, 'color': tag.color}
            for tag in tags
        ])

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocomplete for tag input. Query param: q"""
        query = request.query_params.get('q', '').strip().lower()
        if not query:
            # Return frequently used tags
            tags = self.get_queryset().annotate(
                count=Count('notes', filter=Q(notes__is_deleted=False))
            ).filter(count__gt=0).order_by('-count')[:10]
        else:
            tags = self.get_queryset().filter(name__icontains=query)[:10]
        return Response(TagSerializer(tags, many=True).data)


class MoodNoteViewSet(viewsets.ModelViewSet):
    def get_throttles(self):
        if self.action == 'create':
            return [NoteCreateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == 'list':
            return MoodNoteListSerializer
        return MoodNoteSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MoodNote.objects.none()
        qs = MoodNote.objects.filter(user=self.request.user, is_deleted=False)
        if self.action == 'list':
            params = self.request.query_params
            qs = search_notes(
                qs,
                search=params.get('search'),
                tag=params.get('tag'),
                sentiment_min=params.get('sentiment_min'),
                sentiment_max=params.get('sentiment_max'),
                stress_min=params.get('stress_min'),
                stress_max=params.get('stress_max'),
                date_from=params.get('date_from'),
                date_to=params.get('date_to'),
            )
        elif self.action == 'retrieve':
            qs = qs.prefetch_related('attachments')
        return qs

    def _run_ai_analysis(self, note):
        """Schedule AI sentiment analysis to run in a background thread.

        Returns immediately so the HTTP response isn't blocked by the
        5-15 s OpenAI roundtrip (sentiment + RAG retrieval + feedback gen).
        The note row is updated when the analysis finishes; the frontend
        listens for the `note_analyzed` WebSocket event to refresh its
        view, or falls back to a one-shot GET /notes/{id}/ poll a few
        seconds later. AI engine has its own three-tier fallback so a
        failed OpenAI call still produces some feedback.
        """
        # `threading` and `transaction` are imported at module-level. Defer
        # the thread spawn until the outer DB transaction commits, otherwise
        # otherwise the thread can race against the SELECT and see a
        # row that doesn't exist yet (PostgreSQL read-committed default).
        transaction.on_commit(
            lambda: threading.Thread(
                target=_ai_analysis_worker,
                args=(note.id, note.user_id),
                daemon=True,
            ).start()
        )

    def _invalidate_user_cache(self):
        """Invalidate analytics and calendar caches for the current user.

        Previously only deleted the {week,month}_{7,30} permutations because
        those are the common defaults — but any custom (period, lookback)
        pair the user picked would keep its 5-minute stale cache, so new
        tags / activity correlations could disappear from the dashboard
        until TTL expired. 2026-05-24: switched to an explicit list that
        covers every period × lookback option offered by the UI (see
        DashboardPage.jsx where lookback ∈ {7,14,30,60,90}).
        """
        uid = self.request.user.id
        now = timezone.now()
        keys = []
        for period in ('week', 'month'):
            for lookback in (7, 14, 30, 60, 90):
                keys.append(f'analytics_{uid}_{period}_{lookback}')
        keys.append(f'calendar_{uid}_{now.year}_{now.month}')
        cache.delete_many(keys)

    def perform_create(self, serializer):
        note = serializer.save(user=self.request.user)
        self._run_ai_analysis(note)
        self._invalidate_user_cache()
        # Streak update stays inline — it's a single UPDATE (~50ms vs
        # check_achievements's ~25 queries) and the streak count needs to
        # be accurate immediately so the X-Streak-Milestone toast lands
        # on the same response.
        try:
            from api.services.streaks import update_streak, get_streak_milestone
            streak = update_streak(self.request.user)
            milestone = get_streak_milestone(streak.current_streak)
            if milestone:
                self._streak_milestone = milestone
        except Exception as e:
            logger.warning('Streak update failed for user %s: %s', self.request.user.pk, e)
        # Achievement check goes to a background thread — see _post_save_worker.
        # Unlocks still notify the user via the existing WebSocket fan-out
        # (`_emit_unlock_notifications` inside check_achievements).
        user_id = self.request.user.id
        transaction.on_commit(
            lambda: threading.Thread(
                target=_post_save_worker,
                args=(user_id,),
                daemon=True,
            ).start()
        )

    def perform_update(self, serializer):
        note = serializer.save()
        self._run_ai_analysis(note)
        self._invalidate_user_cache()

    def create(self, request, *args, **kwargs):
        self._new_achievements = []
        self._streak_milestone = None
        response = super().create(request, *args, **kwargs)
        if self._new_achievements:
            response['X-New-Achievements'] = ','.join(self._new_achievements)
        if self._streak_milestone:
            response['X-Streak-Milestone'] = self._streak_milestone['id']
        # Crisis-keyword detection. We do NOT block the save — note stays
        # written exactly as the user wrote it, but the response carries a
        # flag the frontend uses to overlay a hotline banner. A staff-only
        # audit log entry also lands so we can follow up if needed.
        try:
            from api.services.crisis_detector import detect_crisis, crisis_response_payload
            text = str(request.data.get('content', '') or '')
            if detect_crisis(text) and response.data:
                response.data.update(crisis_response_payload())
                from api.services.audit import log_action
                log_action(request.user, 'crisis_keyword_detected_note', request=request)
        except Exception:
            logger.exception('Crisis detector failure on note create')
        return response

    @action(detail=True, methods=['post'])
    def toggle_pin(self, request, pk=None):
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=['is_pinned'])
        return Response({'is_pinned': note.is_pinned})

    @action(detail=True, methods=['post'])
    def reanalyze(self, request, pk=None):
        """Re-analyze note with attached images using the vision LLM.

        Scheduled to run in the background — same async pattern as
        perform_create. Frontend polls or listens for the
        `note_analyzed` WebSocket event to refresh.
        """
        note = self.get_object()
        # FileField.url returns a relative path (``/media/xxx.jpg``). The
        # vision LLM lives on a separate host (llm_server) and cannot resolve
        # that path; it MUST receive an absolute URL. Use the incoming
        # request's host so dev/prod both work without a hardcoded base.
        image_urls = [
            request.build_absolute_uri(att.file.url)
            for att in note.attachments.filter(file_type='image')[:3]
        ]
        if image_urls and note.content:
            import threading
            threading.Thread(
                target=_vision_analysis_worker,
                args=(note.id, note.user_id, image_urls),
                daemon=True,
            ).start()
        return Response(MoodNoteSerializer(note, context={'request': request}).data)

    def perform_destroy(self, instance):
        """Soft delete: mark as deleted instead of permanent removal."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])
        log_action(self.request.user, 'note_delete', self.request, 'MoodNote', instance.pk)

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return error_response('provide_note_ids', 'Please provide a list of note IDs to delete.')
        if len(ids) > MAX_BATCH_DELETE:
            return error_response('batch_delete_limit', f'Cannot delete more than {MAX_BATCH_DELETE} notes at once.')
        updated = MoodNote.objects.filter(user=request.user, id__in=ids, is_deleted=False).update(
            is_deleted=True, deleted_at=timezone.now()
        )
        return Response({'deleted': updated})

    @action(detail=False, methods=['get'])
    def trash(self, request):
        """List soft-deleted notes with pagination.

        prefetch_related('tags') avoids an N+1: MoodNoteListSerializer
        nests TagSerializer(many=True) which would otherwise fire one
        extra SELECT per row.
        """
        qs = MoodNote.objects.filter(
            user=request.user, is_deleted=True
        ).prefetch_related('tags').order_by('-deleted_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MoodNoteListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MoodNoteListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted note."""
        try:
            note = MoodNote.objects.get(pk=pk, user=request.user, is_deleted=True)
        except MoodNote.DoesNotExist:
            return error_response('note_not_found_trash', 'Note not found in trash.', 404)
        note.is_deleted = False
        note.deleted_at = None
        note.save(update_fields=['is_deleted', 'deleted_at'])
        log_action(request.user, 'note_restore', request, 'MoodNote', note.pk)
        return Response(MoodNoteSerializer(note, context={'request': request}).data)

    @action(detail=True, methods=['delete'], url_path='permanent-delete')
    def permanent_delete(self, request, pk=None):
        """Permanently delete a trashed note."""
        try:
            note = MoodNote.objects.get(pk=pk, user=request.user, is_deleted=True)
        except MoodNote.DoesNotExist:
            return error_response('note_not_found_trash', 'Note not found in trash.', 404)
        log_action(request.user, 'note_permanent_delete', request, 'MoodNote', note.pk)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteAttachmentUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadThrottle]

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_USER_ATTACHMENTS = 500
    ALLOWED_TYPES = {'image'}
    # Magic number signatures for allowed image formats
    IMAGE_SIGNATURES = [
        (b'\xff\xd8\xff', 'image/jpeg'),
        (b'\x89PNG\r\n\x1a\n', 'image/png'),
        (b'GIF87a', 'image/gif'),
        (b'GIF89a', 'image/gif'),
        (b'BM', 'image/bmp'),
    ]

    @transaction.atomic
    def post(self, request, note_id):
        try:
            note = MoodNote.objects.select_for_update().get(id=note_id, user=request.user)
        except MoodNote.DoesNotExist:
            return error_response('note_not_found', 'Note not found.', 404)

        file = request.FILES.get('file')
        if not file:
            return error_response('upload_file_required', 'Please upload a file.')

        if file.size > self.MAX_FILE_SIZE:
            return error_response('file_too_large', 'File size cannot exceed 10MB.')

        # Check attachment count quota (select_for_update prevents race condition)
        existing_count = NoteAttachment.objects.filter(note__user=request.user).count()
        if existing_count >= self.MAX_USER_ATTACHMENTS:
            return error_response('attachment_limit', 'Attachment limit reached (500).')

        mime_type = file.content_type or mimetypes.guess_type(file.name)[0] or ''
        file_type = mime_type.split('/')[0]
        if file_type not in self.ALLOWED_TYPES:
            return error_response('image_only', 'Only image files are allowed.')

        # Validate file content via magic number (prevent MIME spoofing)
        header = file.read(16)
        file.seek(0)
        is_webp = header[:4] == b'RIFF' and header[8:12] == b'WEBP'
        if not is_webp and not any(header.startswith(sig) for sig, _ in self.IMAGE_SIGNATURES):
            return error_response('invalid_file_content', 'File content does not match an image format.')

        attachment = NoteAttachment.objects.create(
            note=note,
            file=file,
            file_type=file_type,
            original_name=file.name,
        )
        return Response(NoteAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


class ShareNoteView(APIView):
    def post(self, request, note_id):
        try:
            note = MoodNote.objects.get(id=note_id, user=request.user)
        except MoodNote.DoesNotExist:
            return error_response('note_not_found', 'Note not found.', 404)

        counselor_id = request.data.get('counselor_user_id') or request.data.get('counselor_id')
        is_anonymous = request.data.get('is_anonymous', False)

        if not counselor_id:
            return error_response('counselor_id_required', 'Counselor ID is required.')

        # Verify the target is an approved counselor (accept either profile pk or user pk)
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            try:
                profile = CounselorProfile.objects.get(user_id=counselor_id, status='approved')
            except CounselorProfile.DoesNotExist:
                return error_response('counselor_not_approved', 'Counselor not found or not approved.', 404)

        counselor_user_id = profile.user_id

        shared, created = SharedNote.objects.get_or_create(
            note=note,
            shared_with_id=counselor_user_id,
            defaults={'is_anonymous': is_anonymous},
        )
        if not created:
            return error_response('already_shared', 'This note has already been shared.', 409)

        # Notify counselor
        author_name = 'Anonymous' if is_anonymous else request.user.username
        create_notification_if_enabled(
            User.objects.get(pk=counselor_user_id), 'share',
            title='Note shared with you',
            message=f'{author_name} shared a note with you.',
            data={
                'shared_note_id': shared.id,
                'note_id': note.id,
                'author_name': author_name,
            },
        )

        return Response(SharedNoteSerializer(shared).data, status=status.HTTP_201_CREATED)


class SharedNotesReceivedView(generics.ListAPIView):
    serializer_class = SharedNoteSerializer

    def get_queryset(self):
        return SharedNote.objects.filter(shared_with=self.request.user).select_related('note', 'note__user')


class NoteSharesListView(generics.ListAPIView):
    """GET /notes/{note_id}/shares/ — list shares for a note (owner only)."""
    serializer_class = SharedNoteSerializer

    def get_queryset(self):
        note_id = self.kwargs['note_id']
        return SharedNote.objects.filter(
            note_id=note_id, note__user=self.request.user,
        ).select_related('note', 'note__user', 'shared_with')


class UnshareNoteView(APIView):
    """DELETE /notes/{note_id}/unshare/{share_id}/ — remove a share (owner only)."""

    def delete(self, request, note_id, share_id):
        try:
            share = SharedNote.objects.get(
                id=share_id, note_id=note_id, note__user=request.user,
            )
        except SharedNote.DoesNotExist:
            return error_response('share_not_found', 'Share not found.', 404)
        share.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExportPDFView(APIView):
    throttle_classes = [ExportThrottle]

    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from and date_to and date_from > date_to:
            return error_response('date_from_before_to', 'date_from must be before date_to.')
        lang = request.query_params.get('lang', 'zh-TW')
        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        buf = generate_notes_pdf(qs, date_from=date_from, date_to=date_to, user=request.user, lang=lang)
        return FileResponse(
            buf,
            as_attachment=True,
            filename=f'heartbox_{date_from or "all"}_{date_to or "now"}.pdf',
            content_type='application/pdf',
        )


class ExportDataView(APIView):
    """Export all user data as JSON (GDPR compliance)."""
    throttle_classes = [ExportThrottle]

    def get(self, request):
        import json

        user = request.user
        notes = MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at')[:MAX_EXPORT_NOTES]

        data = {
            'user': {
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined.isoformat(),
            },
            'notes': [],
        }

        for note in notes:
            meta = note.metadata or {}
            note_data = {
                'id': note.id,
                'content': note.content,
                'sentiment_score': note.sentiment_score,
                'stress_index': note.stress_index,
                'ai_feedback': note.ai_feedback,
                'is_pinned': note.is_pinned,
                'metadata': meta,
                'created_at': note.created_at.isoformat(),
                'updated_at': note.updated_at.isoformat(),
            }
            data['notes'].append(note_data)

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json',
        )
        response['Content-Disposition'] = f'attachment; filename="heartbox_export_{user.username}.json"'
        return response


class ExportCSVView(APIView):
    """Export all user notes as CSV."""
    throttle_classes = [ExportThrottle]

    def get(self, request):
        user = request.user
        notes = MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at')[:MAX_EXPORT_NOTES]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['ID', 'Content', 'Sentiment', 'Stress', 'Tags', 'Weather', 'Temperature', 'Pinned', 'AI_Feedback', 'Created', 'Updated'])

        for note in notes:
            meta = note.metadata or {}
            writer.writerow([
                note.id,
                note.content,
                note.sentiment_score,
                note.stress_index,
                ','.join(meta.get('tags', [])),
                meta.get('weather', ''),
                meta.get('temperature', ''),
                note.is_pinned,
                note.ai_feedback or '',
                note.created_at.isoformat(),
                note.updated_at.isoformat() if note.updated_at else '',
            ])

        response = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="heartbox_export_{user.username}.csv"'
        return response


class OnThisDayView(APIView):
    """Get notes from previous years on this day."""

    def get(self, request):
        from api.services.reviews import get_on_this_day
        date_str = request.query_params.get('date')

        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
        else:
            date = None

        results = get_on_this_day(request.user, date)
        return Response(results)


# How many rows we ingest synchronously before falling back to a Celery
# background job. Tuned so most everyday imports (a few weeks of journal
# entries) complete inline; bulk migrations from Day One / Journey go async.
SYNC_IMPORT_LIMIT = 500


class PreviewCSVView(APIView):
    """Preview an import file (CSV or JSON) without writing anything.

    Returns total row count, the first 5 rows, the discovered columns, and a
    suggested column-to-standard-field mapping. The frontend pre-fills its
    mapping dropdowns from `suggested_mapping`.
    """
    throttle_classes = [GeneralWriteThrottle]

    def post(self, request):
        from ..services.import_service import detect_format, parse_file, suggest_mapping

        file = request.FILES.get('file')
        if not file:
            return error_response('error.upload_file_required', 'A file is required.', 400)

        if not detect_format(file.name):
            return error_response('csv_invalid_format', 'Only .csv and .json files are accepted.', 400)

        try:
            blob = file.read()
            fmt, columns, rows = parse_file(file.name, blob)
        except ValueError as e:
            return error_response('csv_parse_error', str(e), 400)
        except Exception as e:
            logger.exception('Import preview error')
            return error_response('csv_parse_error', f'Could not parse file: {e}', 400)

        return Response({
            'format': fmt,
            'total_rows': len(rows),
            'preview_rows': rows[:5],
            'columns': columns,
            'suggested_mapping': suggest_mapping(columns),
            'sync_limit': SYNC_IMPORT_LIMIT,
        })


class ImportCSVView(APIView):
    """Import notes from a CSV / JSON file.

    Small files (≤ SYNC_IMPORT_LIMIT rows) are processed inline so the
    frontend gets an instant ``{imported, errors}`` response. Larger files
    are staged on disk, an ``ImportJob`` is created, and ``import_notes_task``
    is dispatched — the response then carries ``{job_id, status: 'pending'}``
    and the frontend polls ImportJobStatusView for progress.

    Honors a JSON ``mapping`` param of shape ``{<source column>: <target>}``
    where target is one of date / content / mood / stress / tags / weather /
    temperature / _ignore. Without one, the importer falls back to
    DEFAULT_COLUMN_MAP from import_service.
    """
    throttle_classes = [GeneralWriteThrottle]

    def post(self, request):
        import json as _json
        import os
        import secrets

        from django.conf import settings
        from django.utils import timezone as tz

        from ..models import ImportJob
        from ..services.import_service import (
            detect_format, ingest_rows, parse_file,
        )
        from ..tasks import import_notes_task

        file = request.FILES.get('file')
        if not file:
            return error_response('error.upload_file_required', 'A file is required.', 400)

        if not detect_format(file.name):
            return error_response('csv_invalid_format', 'Only .csv and .json files are accepted.', 400)

        # Optional user mapping arrives as a JSON-encoded string in form data.
        mapping = None
        raw_mapping = request.data.get('mapping')
        if raw_mapping:
            try:
                mapping = _json.loads(raw_mapping) if isinstance(raw_mapping, str) else dict(raw_mapping)
                if not isinstance(mapping, dict):
                    raise ValueError('mapping must be an object')
            except (ValueError, TypeError) as e:
                return error_response('csv_invalid_mapping', f'Invalid mapping payload: {e}', 400)

        blob = file.read()
        try:
            fmt, _cols, rows = parse_file(file.name, blob)
        except ValueError as e:
            return error_response('csv_parse_error', str(e), 400)
        except Exception as e:
            logger.exception('Import parse error')
            return error_response('csv_parse_error', f'Could not parse file: {e}', 400)

        # --- Sync path: small file, do it now ---
        if len(rows) <= SYNC_IMPORT_LIMIT:
            created, errors = ingest_rows(request.user, rows, mapping=mapping)
            if created > 0:
                uid = request.user.id
                now = tz.now()
                cache.delete_many([
                    f'analytics_{uid}_week_30',
                    f'analytics_{uid}_month_30',
                    f'analytics_{uid}_week_7',
                    f'calendar_{uid}_{now.year}_{now.month}',
                ])
            return Response({
                'mode': 'sync',
                'imported': created,
                'errors': errors[:10],
                'total_rows': len(rows),
            })

        # --- Async path: stage file under MEDIA_ROOT/imports/ and dispatch ---
        imports_dir = os.path.join(settings.MEDIA_ROOT, 'imports')
        os.makedirs(imports_dir, exist_ok=True)
        suffix = '.json' if fmt == 'json' else '.csv'
        storage_key = os.path.join('imports', f'{secrets.token_hex(8)}{suffix}')
        with open(os.path.join(settings.MEDIA_ROOT, storage_key), 'wb') as fh:
            fh.write(blob)

        job = ImportJob.objects.create(
            user=request.user,
            status='pending',
            fmt=fmt,
            filename=file.name,
            storage_key=storage_key,
            mapping=mapping or {},
            total_rows=len(rows),
        )

        # Dispatch path: prefer Celery when a real broker is configured (Redis
        # via REDIS_URL or CELERY_BROKER_URL), otherwise spawn a background
        # thread so local dev / Cloud Run without Redis still gets non-blocking
        # imports + working polling. The thread dies with the gunicorn worker;
        # that's fine here since the prod path always has a real broker.
        import os
        import threading
        broker_configured = bool(os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL'))
        if broker_configured:
            try:
                import_notes_task.delay(job.id)
            except Exception:
                logger.warning('Celery broker dispatch failed; falling back to thread for job %d', job.id)
                threading.Thread(target=import_notes_task, args=(job.id,), daemon=True).start()
        else:
            threading.Thread(target=import_notes_task, args=(job.id,), daemon=True).start()

        return Response({
            'mode': 'async',
            'job_id': job.id,
            'status': 'pending',
            'total_rows': len(rows),
        })


class ImportJobStatusView(APIView):
    """Poll endpoint for an ImportJob owned by the requesting user."""
    throttle_classes = [GeneralWriteThrottle]

    def get(self, request, pk):
        from ..models import ImportJob
        try:
            job = ImportJob.objects.get(pk=pk, user=request.user)
        except ImportJob.DoesNotExist:
            return error_response('import_job_not_found', 'Import job not found.', 404)

        return Response({
            'job_id': job.id,
            'status': job.status,
            'fmt': job.fmt,
            'filename': job.filename,
            'total_rows': job.total_rows,
            'processed_rows': job.processed_rows,
            'imported_count': job.imported_count,
            'progress_percent': job.progress_percent,
            'errors': (job.errors or [])[:10],
            'error_message': job.error_message,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
        })
