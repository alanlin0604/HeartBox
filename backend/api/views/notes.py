"""Mood notes, tags, attachments, sharing, import/export endpoints.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import csv
import io
import mimetypes
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
        """Run AI sentiment analysis on a note (graceful degradation)."""
        try:
            from api.services.ai_engine import ai_engine
            plaintext = note.content
            if plaintext:
                result = ai_engine.analyze(plaintext)
                note.sentiment_score = result['sentiment_score']
                note.stress_index = result['stress_index']
                note.ai_feedback = result['ai_feedback']
                note.save(update_fields=['sentiment_score', 'stress_index', 'ai_feedback'])
        except Exception as e:
            logger.warning('AI analysis failed for note %s: %s', note.pk, e)

    def _invalidate_user_cache(self):
        """Invalidate analytics and calendar caches for the current user."""
        uid = self.request.user.id
        now = timezone.now()
        cache.delete_many([
            f'analytics_{uid}_week_30',
            f'analytics_{uid}_month_30',
            f'analytics_{uid}_week_7',
            f'calendar_{uid}_{now.year}_{now.month}',
        ])

    def perform_create(self, serializer):
        note = serializer.save(user=self.request.user)
        self._run_ai_analysis(note)
        self._invalidate_user_cache()
        # Update journal streak
        try:
            from api.services.streaks import update_streak, get_streak_milestone
            streak = update_streak(self.request.user)
            milestone = get_streak_milestone(streak.current_streak)
            if milestone:
                self._streak_milestone = milestone
        except Exception as e:
            logger.warning('Streak update failed for user %s: %s', self.request.user.pk, e)
        # Auto-check achievements
        try:
            from api.services.achievements import check_achievements
            new_achievements = check_achievements(self.request.user)
            if new_achievements:
                self._new_achievements = new_achievements
        except Exception as e:
            logger.warning('Achievement check failed for user %s: %s', self.request.user.pk, e)

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
        return response

    @action(detail=True, methods=['post'])
    def toggle_pin(self, request, pk=None):
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=['is_pinned'])
        return Response({'is_pinned': note.is_pinned})

    @action(detail=True, methods=['post'])
    def reanalyze(self, request, pk=None):
        """Re-analyze note with attached images using GPT vision."""
        note = self.get_object()
        image_urls = [
            att.file.url for att in note.attachments.filter(file_type='image')[:3]
        ]
        plaintext = note.content
        if image_urls and plaintext:
            try:
                from api.services.ai_engine import ai_engine
                result = ai_engine.analyze_with_images(plaintext, image_urls)
                note.sentiment_score = result['sentiment_score']
                note.stress_index = result['stress_index']
                note.ai_feedback = result['ai_feedback']
                note.save(update_fields=['sentiment_score', 'stress_index', 'ai_feedback'])
            except Exception as e:
                logger.warning('Reanalyze failed for note %s: %s', note.pk, e)
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
        """List soft-deleted notes with pagination."""
        qs = MoodNote.objects.filter(user=request.user, is_deleted=True).order_by('-deleted_at')
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


class PreviewCSVView(APIView):
    """Preview CSV import without actually creating notes"""
    throttle_classes = [GeneralWriteThrottle]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return error_response('error.upload_file_required', 'A file is required.', 400)

        if not file.name.endswith('.csv'):
            return error_response('csv_invalid_format', 'Only CSV files are accepted.', 400)

        try:
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))

            # Get column headers
            fieldnames = reader.fieldnames or []

            # Preview first 5 rows
            preview_rows = []
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                preview_rows.append(dict(row))

            # Count total rows
            reader_count = csv.DictReader(io.StringIO(content))
            total_rows = sum(1 for _ in reader_count)

            # Suggest column mapping
            COLUMN_MAP = {
                'created': 'date',
                'sentiment': 'mood',
                'created_at': 'date',
                'created_date': 'date',
                'entry': 'content',
                'text': 'content',
                'body': 'content',
                'note': 'content',
            }

            suggested_mapping = {}
            for col in fieldnames:
                col_lower = col.strip().lower()
                suggested_mapping[col] = COLUMN_MAP.get(col_lower, col_lower)

            return Response({
                'total_rows': total_rows,
                'preview_rows': preview_rows,
                'columns': fieldnames,
                'suggested_mapping': suggested_mapping,
            })

        except Exception as e:
            logger.exception('CSV preview error')
            return error_response('csv_parse_error', f'Invalid CSV file: {str(e)}', 400)


class ImportCSVView(APIView):
    throttle_classes = [GeneralWriteThrottle]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return error_response('error.upload_file_required', 'A file is required.', 400)

        if not file.name.endswith('.csv'):
            return error_response('csv_invalid_format', 'Only CSV files are accepted.', 400)

        try:
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
        except Exception:
            logger.exception('CSV import parse error')
            return error_response('csv_parse_error', 'Invalid CSV file.', 400)

        # Normalize column names to lowercase for case-insensitive matching
        # Also map export column names to import column names:
        #   Export: ID, Content, Sentiment, Stress, Tags, Weather, Temperature, Pinned, Created
        #   Import: date, content, mood, stress, tags
        COLUMN_MAP = {
            'created': 'date',
            'sentiment': 'mood',
        }

        created_count = 0
        errors = []

        for i, row in enumerate(reader, start=1):
            if i > 1000:  # Limit to 1000 rows
                break

            # Normalize keys: lowercase + map export names to import names
            normalized = {}
            for k, v in row.items():
                if k is None:
                    continue
                key = k.strip().lower()
                key = COLUMN_MAP.get(key, key)
                normalized[key] = (v or '').strip()

            date_str = normalized.get('date', '')
            content_text = normalized.get('content', '')
            mood = normalized.get('mood', '')
            stress = normalized.get('stress', '')

            if not content_text:
                errors.append(f'Row {i}: missing content')
                continue

            note = MoodNote(user=request.user)
            note.set_content(content_text)

            # Parse metadata
            metadata = {}
            if mood:
                metadata['imported_mood'] = mood
            tags = normalized.get('tags', '')
            if tags:
                metadata['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
            weather = normalized.get('weather', '')
            if weather:
                metadata['weather'] = weather
            temperature = normalized.get('temperature', '')
            if temperature:
                metadata['temperature'] = temperature
            note.metadata = metadata

            # Parse stress
            if stress:
                try:
                    stress_val = int(stress)
                    if 0 <= stress_val <= 10:
                        note.stress_index = stress_val
                except ValueError:
                    pass

            # Parse sentiment score (from export format)
            sentiment = normalized.get('mood', '')
            if sentiment:
                try:
                    score = float(sentiment)
                    if -1.0 <= score <= 1.0:
                        note.sentiment_score = score
                except ValueError:
                    pass

            note.save()

            # Parse date — must update AFTER save because auto_now_add
            # ignores manual values during save()
            if date_str:
                try:
                    from django.utils.dateparse import parse_datetime, parse_date
                    parsed = parse_datetime(date_str) or parse_date(date_str)
                    if parsed:
                        from django.utils import timezone as tz
                        if hasattr(parsed, 'hour'):
                            if tz.is_naive(parsed):
                                parsed = tz.make_aware(parsed)
                            MoodNote.objects.filter(pk=note.pk).update(created_at=parsed)
                        else:
                            aware_dt = tz.make_aware(
                                tz.datetime.combine(parsed, tz.datetime.min.time())
                            )
                            MoodNote.objects.filter(pk=note.pk).update(created_at=aware_dt)
                except Exception:
                    logger.exception('CSV import: failed to parse date for row %d', i)

            created_count += 1

        # Invalidate analytics/calendar caches so charts update immediately
        if created_count > 0:
            uid = request.user.id
            now = timezone.now()
            cache.delete_many([
                f'analytics_{uid}_week_30',
                f'analytics_{uid}_month_30',
                f'analytics_{uid}_week_7',
                f'calendar_{uid}_{now.year}_{now.month}',
            ])

        return Response({
            'imported': created_count,
            'errors': errors[:10],  # Return first 10 errors
        })
