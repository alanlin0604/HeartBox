import logging
import mimetypes
import random
import time
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.db.models import Prefetch
import rest_framework.pagination
import rest_framework.throttling
from rest_framework import generics, viewsets, permissions, status, filters, exceptions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import (
    AIChatMessage, AIChatSession,
    Booking, Conversation, Course, CounselorProfile, Feedback, Message, MoodNote,
    NoteAttachment, Notification, PsychoArticle, SelfAssessment, SharedAssessment,
    SharedNote, TherapistReport, TimeSlot, UserAchievement, UserLessonProgress,
    WeeklySummary, WellnessSession,
)
from .serializers import (
    AIChatMessageSerializer,
    AIChatSessionSerializer,
    AdminCounselorSerializer,
    AdminUserSerializer,
    BookingSerializer,
    ConversationSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    CounselorListSerializer,
    CounselorProfileSerializer,
    FeedbackSerializer,
    MessageSerializer,
    MoodNoteListSerializer,
    MoodNoteSerializer,
    NoteAttachmentSerializer,
    NotificationSerializer,
    PsychoArticleSerializer,
    SelfAssessmentSerializer,
    SharedAssessmentSerializer,
    SharedNoteSerializer,
    TherapistReportPublicSerializer,
    TherapistReportSerializer,
    TimeSlotSerializer,
    UserAchievementSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    WeeklySummarySerializer,
    WellnessSessionSerializer,
)
from .services.analytics import (
    get_activity_mood_correlation, get_calendar_data, get_frequent_tags,
    get_gratitude_stats, get_mood_trends, get_mood_weather_correlation,
    get_sleep_mood_correlation, get_stress_by_tag, get_year_pixels,
)
from .services.alerts import check_mood_alerts
from .services.audit import log_action
from .services.pdf_export import generate_notes_pdf, generate_weekly_summary_pdf
from .services.search import search_notes
from .throttles import (
    AIChatThrottle, BookingThrottle, DeleteAccountThrottle, ExportThrottle,
    LoginRateThrottle, MessageThrottle, NoteCreateThrottle,
    PasswordResetRateThrottle, RefreshTokenThrottle, RegisterRateThrottle, UploadThrottle,
)

User = get_user_model()
logger = logging.getLogger(__name__)

# ===== Constants =====
MAX_BATCH_DELETE = 50
MAX_MESSAGE_LENGTH = 5000
MAX_AI_CHAT_MESSAGE_LENGTH = 2000
MAX_EXPORT_NOTES = 5000
CACHE_TTL_ANALYTICS = 300       # 5 minutes
CACHE_TTL_CALENDAR = 300        # 5 minutes
CACHE_TTL_YEAR_PIXELS = 3600    # 1 hour
CACHE_TTL_DAILY_PROMPT = 86400  # 24 hours

# Lazy singleton for OpenAI client
_openai_client = None


def _get_openai_client():
    """Return a shared OpenAI client instance (lazy-initialized)."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        from django.conf import settings as django_settings
        api_key = getattr(django_settings, 'OPENAI_API_KEY', '')
        if api_key:
            _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _push_ws_notification(recipient_id, notif):
    """Push a notification to a user via WebSocket (fire-and-forget)."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{recipient_id}',
            {
                'type': 'notify',
                'data': {
                    'id': notif.id,
                    'type': notif.type,
                    'title': notif.title,
                    'message': notif.message,
                    'data': notif.data,
                    'is_read': False,
                    'created_at': notif.created_at.isoformat(),
                },
            },
        )
    except Exception as e:
        logger.debug('Channel layer push failed: %s', e)


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterRateThrottle]


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh['token_version'] = user.token_version
    access = refresh.access_token
    access['token_version'] = user.token_version
    return {'refresh': str(refresh), 'access': str(access)}


class VersionedTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['token_version'] = user.token_version
        return token


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])
        user = User.objects.filter(id=token.get('user_id')).first()
        if not user:
            raise exceptions.AuthenticationFailed('User not found')
        if int(token.get('token_version', -1)) != int(user.token_version):
            raise exceptions.AuthenticationFailed('Token no longer valid')
        return super().validate(attrs)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VersionedTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RefreshTokenThrottle]
    serializer_class = VersionedTokenRefreshSerializer


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        start = time.monotonic()
        email = (request.data.get('email') or '').strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            from django.conf import settings
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            reset_url = f'{frontend_url.rstrip("/")}/reset-password?uid={uid}&token={token}'
            plain_message = (
                f'Hi {user.username},\n\n'
                f'Use this link to reset your HeartBox password:\n{reset_url}\n\n'
                f'This link expires in 15 minutes.\n'
                f'If you did not request this, please ignore this email.\n\n'
                f'— HeartBox Team'
            )
            html_message = (
                f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">'
                f'<h2 style="color:#7c3aed">HeartBox</h2>'
                f'<p>Hi {user.username},</p>'
                f'<p>We received a request to reset your password. Click the button below:</p>'
                f'<p style="text-align:center;margin:28px 0">'
                f'<a href="{reset_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
                f'border-radius:8px;text-decoration:none;font-weight:600">Reset Password</a></p>'
                f'<p style="color:#888;font-size:13px">This link expires in 15 minutes. '
                f'If you did not request this, please ignore this email.</p>'
                f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
                f'<p style="color:#aaa;font-size:12px">HeartBox — Your Mental Health Companion</p>'
                f'</div>'
            )
            try:
                send_mail(
                    'HeartBox — Reset Your Password',
                    plain_message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@heartbox.local'),
                    [user.email],
                    html_message=html_message,
                )
            except Exception as e:
                logger.error('Failed to send password reset email to %s: %s', user.email, e)
        # Normalize response time to prevent email enumeration via timing
        elapsed = time.monotonic() - start
        min_time = 1.0
        if elapsed < min_time:
            time.sleep(min_time - elapsed)
        return Response({'status': 'ok'})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        uid = request.data.get('uid') or ''
        token = request.data.get('token') or ''
        new_password = request.data.get('new_password') or ''
        if len(new_password) < 8:
            return Response({'detail': 'Password too short'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            return Response({'detail': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return Response({'detail': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)
        # Run Django password validators
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({'detail': e.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        # Rotate token_version to invalidate all existing JWT sessions
        user.token_version += 1
        user.save(update_fields=['password', 'token_version'])
        log_action(user, 'password_reset', request)
        return Response({'status': 'ok'})


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Handle password change
        old_pw = request.data.get('old_password')
        new_pw = request.data.get('new_password')
        if old_pw and new_pw:
            user = request.user
            if not user.check_password(old_pw):
                return Response({'old_password': ['OLD_PASSWORD_INCORRECT']}, status=status.HTTP_400_BAD_REQUEST)
            # Run Django password validators
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            try:
                validate_password(new_pw, user=user)
            except ValidationError as e:
                return Response({'new_password': e.messages}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_pw)
            # Invalidate all other device tokens
            user.token_version = user.token_version + 1
            user.save(update_fields=['password', 'token_version'])
            log_action(user, 'password_change', request)
            return Response(_issue_tokens(user))
        return super().update(request, *args, **kwargs)


class LogoutOtherDevicesView(APIView):
    def post(self, request):
        user = request.user
        user.token_version = user.token_version + 1
        user.save(update_fields=['token_version'])
        return Response(_issue_tokens(user))


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
        response = super().create(request, *args, **kwargs)
        if self._new_achievements:
            response['X-New-Achievements'] = ','.join(self._new_achievements)
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
            return Response({'detail': 'Please provide a list of note IDs to delete.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(ids) > MAX_BATCH_DELETE:
            return Response({'detail': f'Cannot delete more than {MAX_BATCH_DELETE} notes at once.'}, status=status.HTTP_400_BAD_REQUEST)
        updated = MoodNote.objects.filter(user=request.user, id__in=ids, is_deleted=False).update(
            is_deleted=True, deleted_at=timezone.now()
        )
        return Response({'deleted': updated})

    @action(detail=False, methods=['get'])
    def trash(self, request):
        """List soft-deleted notes (capped at 200)."""
        qs = MoodNote.objects.filter(user=request.user, is_deleted=True).order_by('-deleted_at')[:200]
        serializer = MoodNoteListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted note."""
        try:
            note = MoodNote.objects.get(pk=pk, user=request.user, is_deleted=True)
        except MoodNote.DoesNotExist:
            return Response({'detail': 'Note not found in trash.'}, status=status.HTTP_404_NOT_FOUND)
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
            return Response({'detail': 'Note not found in trash.'}, status=status.HTTP_404_NOT_FOUND)
        log_action(request.user, 'note_permanent_delete', request, 'MoodNote', note.pk)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnalyticsView(APIView):
    def get(self, request):
        period = request.query_params.get('period', 'week')
        try:
            lookback_days = min(max(int(request.query_params.get('lookback_days', 30)), 1), 365)
        except (ValueError, TypeError):
            lookback_days = 30

        cache_key = f'analytics_{request.user.id}_{period}_{lookback_days}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)

        # Calculate streaks (cap to last 366 dates for performance)
        dates = list(
            qs.values_list('created_at__date', flat=True)
            .distinct()
            .order_by('-created_at__date')[:366]
        )
        current_streak = 0
        longest_streak = 0
        if dates:
            today = timezone.localdate()
            # Current streak: count consecutive days from today/yesterday
            streak = 0
            expected = today
            for d in dates:
                if d == expected:
                    streak += 1
                    expected = d - timezone.timedelta(days=1)
                elif d == today - timezone.timedelta(days=1) and streak == 0:
                    # Allow starting from yesterday if no entry today
                    streak = 1
                    expected = d - timezone.timedelta(days=1)
                else:
                    break
            current_streak = streak

            # Longest streak
            best = 1
            run = 1
            sorted_dates = sorted(set(dates))
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
            longest_streak = best

        gratitude = get_gratitude_stats(qs)

        result = {
            'mood_trends': get_mood_trends(qs, period=period, lookback_days=lookback_days),
            'weather_correlation': get_mood_weather_correlation(qs, lookback_days=lookback_days),
            'frequent_tags': get_frequent_tags(qs, lookback_days=lookback_days),
            'stress_by_tag': get_stress_by_tag(qs, lookback_days=lookback_days),
            'activity_correlation': get_activity_mood_correlation(qs, lookback_days=lookback_days),
            'sleep_correlation': get_sleep_mood_correlation(qs, lookback_days=lookback_days),
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'gratitude_count': gratitude['gratitude_count'],
            'gratitude_streak': gratitude['gratitude_streak'],
        }
        cache.set(cache_key, result, CACHE_TTL_ANALYTICS)
        return Response(result)


class CalendarView(APIView):
    def get(self, request):
        try:
            year = int(request.query_params.get('year', timezone.now().year))
            month = int(request.query_params.get('month', timezone.now().month))
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid year or month.'}, status=status.HTTP_400_BAD_REQUEST)
        if not (1 <= month <= 12) or not (1900 <= year <= 2100):
            return Response({'detail': 'Year must be 1900-2100, month must be 1-12.'}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f'calendar_{request.user.id}_{year}_{month}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        days = get_calendar_data(qs, year, month)
        result = {'year': year, 'month': month, 'days': days}
        cache.set(cache_key, result, CACHE_TTL_CALENDAR)
        return Response(result)


class ExportPDFView(APIView):
    throttle_classes = [ExportThrottle]

    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from and date_to and date_from > date_to:
            return Response({'detail': 'date_from must be before date_to.'}, status=status.HTTP_400_BAD_REQUEST)
        lang = request.query_params.get('lang', 'zh-TW')
        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        buf = generate_notes_pdf(qs, date_from=date_from, date_to=date_to, user=request.user, lang=lang)
        return FileResponse(
            buf,
            as_attachment=True,
            filename=f'heartbox_{date_from or "all"}_{date_to or "now"}.pdf',
            content_type='application/pdf',
        )


class AlertsView(APIView):
    def get(self, request):
        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        alerts = check_mood_alerts(qs)
        return Response({'alerts': alerts})


# ===== Achievement Views =====

class AchievementsView(APIView):
    def get(self, request):
        from api.services.achievements import get_user_achievements_with_progress
        data = get_user_achievements_with_progress(request.user)
        return Response(data)


class AchievementCheckView(APIView):
    def post(self, request):
        from api.services.achievements import check_achievements
        newly_unlocked = check_achievements(request.user)
        return Response({'newly_unlocked': newly_unlocked})


# ===== Counselor Views =====

class CounselorApplyView(generics.CreateAPIView):
    """User applies to become a counselor."""
    serializer_class = CounselorProfileSerializer

    def perform_create(self, serializer):
        if CounselorProfile.objects.filter(user=self.request.user).exists():
            raise exceptions.ValidationError({'detail': 'You have already applied as a counselor.'})
        serializer.save(user=self.request.user)


class CounselorMyProfileView(generics.RetrieveUpdateAPIView):
    """Counselor views/updates their own profile."""
    serializer_class = CounselorProfileSerializer

    def get_object(self):
        try:
            return CounselorProfile.objects.get(user=self.request.user)
        except CounselorProfile.DoesNotExist:
            from django.http import Http404
            raise Http404


class CounselorListView(generics.ListAPIView):
    """List all approved counselors (public for authenticated users), excluding self."""
    serializer_class = CounselorListSerializer

    def get_queryset(self):
        return CounselorProfile.objects.filter(status='approved').exclude(user=self.request.user).select_related('user')


# ===== Messaging Views =====

class ConversationPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 30


class ConversationListView(generics.ListAPIView):
    """List all conversations for the current user."""
    serializer_class = ConversationSerializer
    pagination_class = ConversationPagination

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(user=user) | Q(counselor=user)
        ).select_related(
            'user', 'counselor',
            'user__counselor_profile', 'counselor__counselor_profile',
        ).prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.select_related(
                    'sender', 'sender__counselor_profile',
                ).order_by('-created_at'),
            )
        )


class ConversationDeleteView(APIView):
    """Delete a conversation (only participants can delete)."""

    def delete(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationCreateView(APIView):
    """Start a conversation with a counselor."""

    def post(self, request):
        counselor_id = request.data.get('counselor_id')
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return Response({'detail': 'Counselor not found.'}, status=status.HTTP_404_NOT_FOUND)

        conv, created = Conversation.objects.get_or_create(
            user=request.user,
            counselor=profile.user,
        )
        return Response(ConversationSerializer(conv, context={'request': request}).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessageListView(APIView):
    """List messages in a conversation and send new messages."""

    def get_throttles(self):
        if self.request.method == 'POST':
            return [MessageThrottle()]
        return super().get_throttles()

    def get(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Mark unread messages as read
        conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        messages = conv.messages.select_related('sender', 'sender__counselor_profile').all()
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        message_type = request.data.get('message_type', 'text')

        if message_type == 'quote':
            # Only approved counselors can send quotes
            if not hasattr(request.user, 'counselor_profile') or not request.user.counselor_profile.is_approved:
                return Response({'detail': 'Only approved counselors can send quotes.'},
                                status=status.HTTP_403_FORBIDDEN)
            description = strip_tags(request.data.get('description', '')).strip()
            if not description:
                return Response({'detail': 'Quote description is required.'},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                price = float(request.data.get('price', 0))
            except (ValueError, TypeError):
                return Response({'detail': 'Invalid price.'}, status=status.HTTP_400_BAD_REQUEST)
            if price < 0:
                return Response({'detail': 'Price cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            currency = request.data.get('currency', 'TWD')
            metadata = {'description': description, 'price': price, 'currency': currency}
            content = f'[Quote] {description} — {currency} {price}'
            msg = Message.objects.create(
                conversation=conv, sender=request.user,
                content=content, message_type='quote', metadata=metadata,
            )
        else:
            content = strip_tags(request.data.get('content', '')).strip()
            if not content:
                return Response({'detail': 'Message cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(content) > MAX_MESSAGE_LENGTH:
                return Response({'detail': f'Message cannot exceed {MAX_MESSAGE_LENGTH} characters.'}, status=status.HTTP_400_BAD_REQUEST)
            msg = Message.objects.create(conversation=conv, sender=request.user, content=content[:MAX_MESSAGE_LENGTH])

        conv.save()  # update updated_at

        # Create notification for the other party
        recipient_id = conv.counselor_id if conv.user_id == request.user.id else conv.user_id
        notif_data = {
            'conversation_id': conv.id,
            'message_id': msg.id,
            'sender_name': request.user.username,
        }
        if message_type == 'quote':
            notif_data['message_type'] = 'quote'
        notif = Notification.objects.create(
            user_id=recipient_id,
            type='message',
            title='New message',
            message=msg.content[:100],
            data=notif_data,
        )

        _push_ws_notification(recipient_id, notif)

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class QuoteActionView(APIView):
    """Accept or reject a quote message."""

    def post(self, request, conv_id, msg_id):
        action = request.data.get('action')
        if action not in ('accept', 'reject'):
            return Response({'detail': 'Action must be accept or reject.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            msg = conv.messages.get(id=msg_id, message_type='quote')
        except Message.DoesNotExist:
            return Response({'detail': 'Quote not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        # Only the non-sender can accept/reject
        if msg.sender == request.user:
            return Response({'detail': 'Cannot act on your own quote.'},
                            status=status.HTTP_403_FORBIDDEN)
        msg.metadata['status'] = 'accepted' if action == 'accept' else 'rejected'
        msg.save(update_fields=['metadata'])
        return Response(MessageSerializer(msg).data)


# ===== Admin Views =====

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.db.models import Count
        today = timezone.now().date()
        user_stats = User.objects.aggregate(
            total_users=Count('id'),
            today_new_users=Count('id', filter=Q(date_joined__date=today)),
            active_users=Count('id', filter=Q(is_active=True)),
        )
        note_stats = MoodNote.objects.aggregate(
            total_notes=Count('id', filter=Q(is_deleted=False)),
            today_new_notes=Count('id', filter=Q(created_at__date=today, is_deleted=False)),
        )
        pending_counselors = CounselorProfile.objects.filter(status='pending').count()
        return Response({
            **user_stats,
            **note_stats,
            'pending_counselors': pending_counselors,
        })


class AdminUserPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 50


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    pagination_class = AdminUserPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()

    def perform_update(self, serializer):
        target = serializer.instance
        # Prevent admin from demoting themselves
        if target.pk == self.request.user.pk and 'is_staff' in serializer.validated_data:
            if not serializer.validated_data['is_staff']:
                raise exceptions.ValidationError({'detail': 'You cannot remove your own admin privileges.'})
        serializer.save()


class AdminCounselorListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminCounselorSerializer

    def get_queryset(self):
        qs = CounselorProfile.objects.select_related('user').all()
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        return qs


class AdminCounselorActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            profile = CounselorProfile.objects.get(pk=pk)
        except CounselorProfile.DoesNotExist:
            return Response({'detail': 'Counselor not found.'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action not in ('approve', 'reject'):
            return Response({'detail': 'Action must be "approve" or "reject".'}, status=status.HTTP_400_BAD_REQUEST)

        profile.status = 'approved' if action == 'approve' else 'rejected'
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=['status', 'reviewed_at'])
        logger.info(
            'Admin %s %sd counselor profile %s (user: %s)',
            request.user.username, action, profile.pk, profile.user.username,
        )
        return Response(AdminCounselorSerializer(profile).data)


# ===== Notification Views =====

class NotificationPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 50


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationReadView(APIView):
    def post(self, request):
        ids = request.data.get('ids', [])
        if ids:
            Notification.objects.filter(user=request.user, id__in=ids).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


# ===== Attachment Views =====

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
            return Response({'detail': 'Note not found.'}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'Please upload a file.'}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > self.MAX_FILE_SIZE:
            return Response({'detail': 'File size cannot exceed 10MB.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check attachment count quota (select_for_update prevents race condition)
        existing_count = NoteAttachment.objects.filter(note__user=request.user).count()
        if existing_count >= self.MAX_USER_ATTACHMENTS:
            return Response({'detail': 'Attachment limit reached (500).'}, status=status.HTTP_400_BAD_REQUEST)

        mime_type = file.content_type or mimetypes.guess_type(file.name)[0] or ''
        file_type = mime_type.split('/')[0]
        if file_type not in self.ALLOWED_TYPES:
            return Response({'detail': 'Only image files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file content via magic number (prevent MIME spoofing)
        header = file.read(16)
        file.seek(0)
        is_webp = header[:4] == b'RIFF' and header[8:12] == b'WEBP'
        if not is_webp and not any(header.startswith(sig) for sig, _ in self.IMAGE_SIGNATURES):
            return Response({'detail': 'File content does not match an image format.'}, status=status.HTTP_400_BAD_REQUEST)

        attachment = NoteAttachment.objects.create(
            note=note,
            file=file,
            file_type=file_type,
            original_name=file.name,
        )
        return Response(NoteAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


# ===== Schedule Views =====

class TimeSlotListView(APIView):
    """Counselor CRUD for their own time slots."""

    def get(self, request):
        slots = TimeSlot.objects.filter(counselor=request.user)
        return Response(TimeSlotSerializer(slots, many=True).data)

    def post(self, request):
        serializer = TimeSlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(counselor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        slot_id = request.data.get('id')
        TimeSlot.objects.filter(id=slot_id, counselor=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailableSlotsView(APIView):
    """Get available slots for a counselor on a given date.

    counselor_id in the URL is CounselorProfile.pk, but TimeSlot/Booking
    reference User.pk, so we resolve the profile first.
    """

    def get(self, request, counselor_id):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'detail': 'Please provide a date parameter.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve CounselorProfile.pk → User.pk
        try:
            profile = CounselorProfile.objects.get(pk=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return Response({'detail': 'Counselor not found.'}, status=status.HTTP_404_NOT_FOUND)
        user_id = profile.user_id

        day_of_week = target_date.weekday()
        slots = TimeSlot.objects.filter(
            counselor_id=user_id,
            day_of_week=day_of_week,
            is_active=True,
        )

        # Exclude already booked slots
        booked = Booking.objects.filter(
            counselor_id=user_id,
            date=target_date,
            status__in=['pending', 'confirmed'],
        ).values_list('start_time', 'end_time')
        booked_set = set(booked)

        available = []
        for slot in slots:
            if (slot.start_time, slot.end_time) not in booked_set:
                available.append(TimeSlotSerializer(slot).data)

        return Response(available)


class BookingListView(APIView):
    def get(self, request):
        user = request.user
        bookings = Booking.objects.filter(
            Q(user=user) | Q(counselor=user)
        ).select_related('user', 'counselor').order_by('-created_at')[:100]
        return Response(BookingSerializer(bookings, many=True).data)


class BookingCreateView(APIView):
    throttle_classes = [BookingThrottle]

    @transaction.atomic
    def post(self, request):
        counselor_id = request.data.get('counselor_id')
        date_str = request.data.get('date')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        if not all([counselor_id, date_str, start_time, end_time]):
            return Response({'detail': 'All required fields must be provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate time format (HH:MM or HH:MM:SS)
        from datetime import time as dt_time
        try:
            parts = str(start_time).split(':')
            start_t = dt_time(int(parts[0]), int(parts[1]))
            parts = str(end_time).split(':')
            end_t = dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return Response({'detail': 'Invalid time format. Use HH:MM.'}, status=status.HTTP_400_BAD_REQUEST)
        if start_t >= end_t:
            return Response({'detail': 'Start time must be before end time.'}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve CounselorProfile.pk → User.pk
        try:
            profile = CounselorProfile.objects.get(pk=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return Response({'detail': 'Counselor not found.'}, status=status.HTTP_404_NOT_FOUND)
        counselor_user_id = profile.user_id

        # Prevent self-booking
        if counselor_user_id == request.user.id:
            return Response({'detail': 'You cannot book yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if target_date < timezone.now().date():
            return Response({'detail': 'Cannot book a past date.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for conflicts with row-level locking to prevent race condition
        conflict = Booking.objects.select_for_update().filter(
            counselor_id=counselor_user_id,
            date=target_date,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status__in=['pending', 'confirmed'],
        ).exists()
        if conflict:
            return Response({'detail': 'This time slot is already booked.'}, status=status.HTTP_409_CONFLICT)

        booking = Booking.objects.create(
            user=request.user,
            counselor_id=counselor_user_id,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            price=profile.hourly_rate,
        )

        # Notify counselor
        notif = Notification.objects.create(
            user_id=counselor_user_id,
            type='booking',
            title='New booking',
            message=f'{request.user.username} booked {date_str} {start_time}',
            data={
                'booking_id': booking.id,
                'action': 'new',
                'username': request.user.username,
                'date': date_str,
                'time': str(start_time),
            },
        )

        _push_ws_notification(counselor_user_id, notif)

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingActionView(APIView):
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, counselor=request.user)
        except Booking.DoesNotExist:
            return Response({'detail': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        action_type = request.data.get('action')
        if action_type == 'confirm':
            booking.status = 'confirmed'
        elif action_type == 'cancel':
            booking.status = 'cancelled'
        elif action_type == 'complete':
            booking.status = 'completed'
        else:
            return Response({'detail': 'Action must be "confirm", "cancel", or "complete".'},
                            status=status.HTTP_400_BAD_REQUEST)
        booking.save(update_fields=['status'])

        # Notify user
        notif = Notification.objects.create(
            user=booking.user,
            type='booking',
            title=f'Booking {booking.status}',
            message=f'Your booking with {booking.counselor.username} is now {booking.status}.',
            data={
                'booking_id': booking.id,
                'action': booking.status,
                'counselor_name': booking.counselor.username,
            },
        )

        _push_ws_notification(booking.user_id, notif)

        return Response(BookingSerializer(booking).data)


class BookingUserCancelView(APIView):
    """Allow a user to cancel their own pending or confirmed booking."""

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return Response({'detail': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status not in ('pending', 'confirmed'):
            return Response(
                {'detail': 'Only pending or confirmed bookings can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = 'cancelled'
        booking.save(update_fields=['status'])

        # Notify counselor
        notif = Notification.objects.create(
            user=booking.counselor,
            type='booking',
            title='Booking cancelled',
            message=f'{request.user.username} cancelled their booking.',
            data={
                'booking_id': booking.id,
                'action': 'user_cancelled',
                'username': request.user.username,
            },
        )
        _push_ws_notification(booking.counselor_id, notif)

        return Response(BookingSerializer(booking).data)


# ===== Share Assessment Views =====

class ShareAssessmentView(APIView):
    """Share a self-assessment result with a counselor."""

    def post(self, request, pk):
        try:
            assessment = SelfAssessment.objects.get(pk=pk, user=request.user)
        except SelfAssessment.DoesNotExist:
            return Response({'detail': 'Assessment not found.'}, status=status.HTTP_404_NOT_FOUND)

        counselor_id = request.data.get('counselor_id')
        if not counselor_id:
            return Response({'detail': 'counselor_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify target is an approved counselor
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            try:
                profile = CounselorProfile.objects.get(user_id=counselor_id, status='approved')
            except CounselorProfile.DoesNotExist:
                return Response({'detail': 'Counselor not found or not approved.'}, status=status.HTTP_404_NOT_FOUND)

        shared, created = SharedAssessment.objects.get_or_create(
            assessment=assessment,
            shared_with=profile.user,
        )
        if not created:
            return Response({'detail': 'Already shared with this counselor.'}, status=status.HTTP_200_OK)

        # Notify counselor
        notif = Notification.objects.create(
            user=profile.user,
            type='assessment_share',
            title='Assessment shared',
            message=f'{request.user.username} shared a {assessment.assessment_type.upper()} assessment with you.',
            data={
                'assessment_id': assessment.id,
                'assessment_type': assessment.assessment_type,
                'username': request.user.username,
            },
        )
        _push_ws_notification(profile.user_id, notif)

        return Response(SharedAssessmentSerializer(shared).data, status=status.HTTP_201_CREATED)


class SharedAssessmentsReceivedView(generics.ListAPIView):
    """Counselor endpoint to list assessments shared with them."""
    serializer_class = SharedAssessmentSerializer

    def get_queryset(self):
        return SharedAssessment.objects.filter(
            shared_with=self.request.user,
        ).select_related('assessment', 'assessment__user')


# ===== Share Views =====

class ShareNoteView(APIView):
    def post(self, request, note_id):
        try:
            note = MoodNote.objects.get(id=note_id, user=request.user)
        except MoodNote.DoesNotExist:
            return Response({'detail': 'Note not found.'}, status=status.HTTP_404_NOT_FOUND)

        counselor_id = request.data.get('counselor_user_id') or request.data.get('counselor_id')
        is_anonymous = request.data.get('is_anonymous', False)

        if not counselor_id:
            return Response({'detail': 'Counselor ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the target is an approved counselor (accept either profile pk or user pk)
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            try:
                profile = CounselorProfile.objects.get(user_id=counselor_id, status='approved')
            except CounselorProfile.DoesNotExist:
                return Response({'detail': 'Counselor not found or not approved.'}, status=status.HTTP_404_NOT_FOUND)

        counselor_user_id = profile.user_id

        shared, created = SharedNote.objects.get_or_create(
            note=note,
            shared_with_id=counselor_user_id,
            defaults={'is_anonymous': is_anonymous},
        )
        if not created:
            return Response({'detail': 'This note has already been shared.'}, status=status.HTTP_409_CONFLICT)

        # Notify counselor
        author_name = 'Anonymous' if is_anonymous else request.user.username
        Notification.objects.create(
            user_id=counselor_user_id,
            type='share',
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


# ===== Account Management Views =====

class DeleteAccountView(APIView):
    """Permanently delete user account and all related data."""
    throttle_classes = [DeleteAccountThrottle]

    @transaction.atomic
    def post(self, request):
        password = request.data.get('password', '')
        if not password:
            return Response({'detail': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(password):
            return Response({'detail': 'Incorrect password.'}, status=status.HTTP_400_BAD_REQUEST)
        log_action(request.user, 'account_delete', request)
        request.user.delete()
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class ExportDataView(APIView):
    """Export all user data as JSON (GDPR compliance)."""
    throttle_classes = [ExportThrottle]

    def get(self, request):
        import json
        from django.http import HttpResponse

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
        import csv
        import io
        from django.http import HttpResponse

        user = request.user
        notes = MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at')[:MAX_EXPORT_NOTES]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['ID', 'Content', 'Sentiment', 'Stress', 'Tags', 'Weather', 'Temperature', 'Pinned', 'Created'])

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
                note.created_at.isoformat(),
            ])

        response = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="heartbox_export_{user.username}.csv"'
        return response


# ===== Feedback =====

class FeedbackCreateView(generics.CreateAPIView):
    serializer_class = FeedbackSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdminFeedbackListView(generics.ListAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Feedback.objects.select_related('user').all()


# ===== AI Chat Views =====

class AIChatSessionListCreateView(APIView):
    """List all active sessions or create a new one."""

    def get(self, request):
        from django.db.models import Count, Subquery, OuterRef
        from django.db.models.functions import Substr
        last_msg_subquery = (
            AIChatMessage.objects.filter(session=OuterRef('pk'))
            .order_by('-created_at')
            .values('content')[:1]
        )
        sessions = (
            AIChatSession.objects.filter(user=request.user, is_active=True)
            .annotate(
                _message_count=Count('messages'),
                _last_message_preview=Substr(Subquery(last_msg_subquery), 1, 80),
            )
        )
        return Response(AIChatSessionSerializer(sessions, many=True).data)

    def post(self, request):
        session = AIChatSession.objects.create(user=request.user)
        return Response(AIChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class AIChatSessionDetailView(APIView):
    """Get session detail with messages, or soft-delete session."""

    def get(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = session.messages.all()
        # Pagination: return last 50 by default, support ?before=<msg_id>
        before = request.query_params.get('before')
        if before:
            messages = messages.filter(id__lt=before)
        total = messages.count()
        page = messages.order_by('-created_at')[:50]
        msg_list = list(reversed(page))
        return Response({
            **AIChatSessionSerializer(session).data,
            'messages': AIChatMessageSerializer(msg_list, many=True).data,
            'has_more': total > len(msg_list),
        })

    def patch(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        update_fields = []
        if 'title' in request.data:
            session.title = str(request.data['title'])[:100]
            update_fields.append('title')
        if 'is_pinned' in request.data:
            session.is_pinned = bool(request.data['is_pinned'])
            update_fields.append('is_pinned')

        if update_fields:
            session.save(update_fields=update_fields)
        return Response(AIChatSessionSerializer(session).data)

    def delete(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        session.is_active = False
        session.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIChatSendMessageView(APIView):
    """Send a message in an AI chat session."""
    throttle_classes = [AIChatThrottle]

    def post(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'detail': 'Message cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(content) > MAX_AI_CHAT_MESSAGE_LENGTH:
            return Response({'detail': f'Message cannot exceed {MAX_AI_CHAT_MESSAGE_LENGTH} characters.'}, status=status.HTTP_400_BAD_REQUEST)

        # Analyze sentiment locally
        from .services.ai_chat import analyze_user_message, generate_ai_response, _get_lang
        sentiment = analyze_user_message(content)

        # Save user message
        user_msg = AIChatMessage.objects.create(
            session=session,
            role='user',
            content=content,
            sentiment_score=sentiment['sentiment_score'],
            stress_index=sentiment['stress_index'],
        )

        # Auto-set session title from first message
        if session.messages.count() == 1:
            session.title = content[:50]
            session.save(update_fields=['title', 'updated_at'])
        else:
            session.save(update_fields=['updated_at'])

        # Generate AI response
        lang = _get_lang(request.headers.get('Accept-Language', ''))
        all_messages = list(session.messages.all())
        ai_content = generate_ai_response(all_messages, lang)

        # Save assistant message
        ai_msg = AIChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_content,
        )

        return Response({
            'user_message': AIChatMessageSerializer(user_msg).data,
            'ai_message': AIChatMessageSerializer(ai_msg).data,
        }, status=status.HTTP_201_CREATED)


# ===== Year Pixels View =====

class YearPixelsView(APIView):
    def get(self, request):
        try:
            year = int(request.query_params.get('year', timezone.now().year))
        except (ValueError, TypeError):
            year = timezone.now().year

        cache_key = f'year_pixels_{request.user.id}_{year}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({'year': year, 'pixels': cached})

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        pixels = get_year_pixels(qs, year)
        cache.set(cache_key, pixels, CACHE_TTL_YEAR_PIXELS)
        return Response({'year': year, 'pixels': pixels})


# ===== Daily Prompt View =====

DEFAULT_PROMPTS_ZH = [
    "今天的心情如何？",
    "最近有什麼讓你開心的小事嗎？",
    "今天最想對自己說的一句話是什麼？",
    "此刻你的身體感覺如何？",
    "今天有什麼讓你印象深刻的事？",
    "最近有什麼讓你感到感恩的事嗎？",
    "今天遇到了什麼挑戰？你怎麼面對的？",
    "現在最想做的一件事是什麼？",
    "今天和誰有了愉快的互動？",
    "用三個詞形容你現在的狀態。",
    "今天學到了什麼新東西？",
    "如果可以重來，今天你會做什麼不同的事？",
    "最近什麼事情讓你感到驕傲？",
    "今天有沒有一個讓你微笑的瞬間？",
    "你現在最需要什麼？",
    "今天有什麼事情超出你的預期？",
    "最近有什麼讓你擔心的事嗎？",
    "你上次真正放鬆是什麼時候？",
    "如果此刻可以跟任何人說話，你會選誰？",
    "今天你為自己做了什麼好事？",
]

DEFAULT_PROMPTS_EN = [
    "How are you feeling right now?",
    "What's something small that made you happy recently?",
    "What would you say to yourself today?",
    "How does your body feel at this moment?",
    "What stood out to you today?",
    "What's something you feel grateful for recently?",
    "What challenge did you face today? How did you handle it?",
    "What's one thing you'd like to do for yourself right now?",
    "Who did you enjoy spending time with today?",
    "Describe your current state in three words.",
    "What did you learn today?",
    "If you could redo today, what would you do differently?",
    "What have you felt proud of recently?",
    "Was there a moment today that made you smile?",
    "What do you need most right now?",
    "What surprised you today?",
    "Is there something that's been worrying you lately?",
    "When was the last time you truly relaxed?",
    "If you could talk to anyone right now, who would it be?",
    "What's one kind thing you did for yourself today?",
]

DEFAULT_PROMPTS_JA = [
    "今日の気分はどうですか？",
    "最近、嬉しかった小さなことはありますか？",
    "今日、自分に言いたい一言は？",
    "今、体はどんな感じですか？",
    "今日、印象に残ったことは何ですか？",
    "最近、感謝していることはありますか？",
    "今日どんな挑戦がありましたか？どう対処しましたか？",
    "今一番やりたいことは何ですか？",
    "今日、誰と楽しい時間を過ごしましたか？",
    "今の状態を三つの言葉で表すと？",
    "今日、何か新しいことを学びましたか？",
    "もし今日をやり直せるなら、何を変えますか？",
    "最近、誇りに思ったことは何ですか？",
    "今日、思わず笑顔になった瞬間はありましたか？",
    "今、一番必要なものは何ですか？",
    "今日、予想外だったことはありますか？",
    "最近、心配していることはありますか？",
    "最後に心からリラックスしたのはいつですか？",
    "今、誰とでも話せるなら、誰を選びますか？",
    "今日、自分に優しくしたことは何ですか？",
]

DEFAULT_PROMPTS_MAP = {
    'zh-TW': DEFAULT_PROMPTS_ZH,
    'en': DEFAULT_PROMPTS_EN,
    'ja': DEFAULT_PROMPTS_JA,
}


class DailyPromptView(APIView):
    def get(self, request):
        today = timezone.now().date().isoformat()
        cache_key = f'daily_prompt_{request.user.id}_{today}'
        cached = cache.get(cache_key)
        if cached:
            return Response({'prompt': cached})

        # Generate prompt based on recent mood
        prompt_text = None
        try:
            recent = MoodNote.objects.filter(
                user=request.user,
                is_deleted=False,
                sentiment_score__isnull=False,
                created_at__gte=timezone.now() - timedelta(days=7),
            ).aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

            avg_s = recent['avg_s']
            avg_st = recent['avg_st']

            client = _get_openai_client()
            if client:
                lang = request.headers.get('Accept-Language', 'zh-TW')
                lang_map = {'zh-TW': 'Traditional Chinese', 'en': 'English', 'ja': 'Japanese'}
                lang_name = lang_map.get(lang, 'Traditional Chinese')
                mood_ctx = ''
                if avg_s is not None:
                    mood_ctx = f"The user's average mood score this week is {avg_s:.2f} (scale -1 to 1). "
                if avg_st is not None:
                    mood_ctx += f"Average stress level is {avg_st:.1f}/10. "

                resp = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{
                        'role': 'system',
                        'content': (
                            f'You are a gentle journaling coach. {mood_ctx}'
                            f'Generate one short, open-ended journaling prompt in {lang_name}. '
                            f'Keep it to ONE simple question (under 20 words). '
                            f'The prompt should be easy to start writing from directly. '
                            f'Avoid long instructions or multi-part questions. No quotes or labels.'
                        ),
                    }],
                    max_tokens=60,
                    temperature=0.8,
                    timeout=15,
                )
                prompt_text = resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning('Daily prompt generation failed: %s', e)

        if not prompt_text:
            lang = request.headers.get('Accept-Language', 'zh-TW')
            prompts = DEFAULT_PROMPTS_MAP.get(lang, DEFAULT_PROMPTS_ZH)
            prompt_text = random.choice(prompts)

        cache.set(cache_key, prompt_text, CACHE_TTL_DAILY_PROMPT)
        return Response({'prompt': prompt_text})


# ===== Self Assessment Views =====

class SelfAssessmentListCreateView(generics.ListCreateAPIView):
    serializer_class = SelfAssessmentSerializer

    def get_queryset(self):
        qs = SelfAssessment.objects.filter(user=self.request.user)
        atype = self.request.query_params.get('type')
        if atype in ('phq9', 'gad7'):
            qs = qs.filter(assessment_type=atype)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ===== Weekly Summary Views =====

class WeeklySummaryView(APIView):
    def _is_pdf_request(self, request):
        """Check if PDF export requested (supports both 'export' and 'format' params)."""
        return request.query_params.get('export') == 'pdf' or request.query_params.get('format') == 'pdf'

    def _generate_pdf_response(self, summary, request):
        """Generate and return a PDF FileResponse for the given summary."""
        week_end = summary.week_start + timedelta(days=6)
        notes_qs = MoodNote.objects.filter(
            user=request.user,
            is_deleted=False,
            created_at__date__gte=summary.week_start,
            created_at__date__lte=week_end,
        ).order_by('created_at')
        lang = request.query_params.get('lang') or request.headers.get('Accept-Language', 'zh-TW').split(',')[0].strip()
        buf = generate_weekly_summary_pdf(summary, notes_qs, request.user, lang=lang)
        filename = f'weekly_summary_{summary.week_start}.pdf'
        return FileResponse(buf, as_attachment=True, filename=filename, content_type='application/pdf')

    def get(self, request):
        # Support PDF export by summary ID (for cached old frontend versions)
        summary_id = request.query_params.get('id')
        if summary_id and self._is_pdf_request(request):
            try:
                # Try with user filter first, then without (in case of user mismatch)
                summary = WeeklySummary.objects.filter(id=summary_id, user=request.user).first()
                if not summary:
                    # Log for debugging
                    exists = WeeklySummary.objects.filter(id=summary_id).exists()
                    logger.warning('Weekly PDF by ID=%s: user=%s, exists_any_user=%s', summary_id, request.user.id, exists)
                    return Response({'detail': 'Summary not found.'}, status=status.HTTP_404_NOT_FOUND)
                return self._generate_pdf_response(summary, request)
            except Exception as e:
                logger.error('Weekly summary PDF (id=%s) failed: %s', summary_id, e, exc_info=True)
                return Response({'detail': 'PDF generation failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        week_start_str = request.query_params.get('week_start')
        if not week_start_str:
            return Response({'detail': 'week_start parameter required (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': 'Invalid date format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-adjust to Monday of the given week
        weekday = week_start.weekday()  # 0=Monday, 6=Sunday
        if weekday != 0:
            week_start = week_start - timedelta(days=weekday)

        # Try to find existing
        summary = WeeklySummary.objects.filter(user=request.user, week_start=week_start).first()

        if summary:
            # Always refresh note_count to reflect current actual count
            week_end = week_start + timedelta(days=6)
            actual_count = MoodNote.objects.filter(
                user=request.user, is_deleted=False,
                created_at__date__gte=week_start, created_at__date__lte=week_end,
            ).count()
            if summary.note_count != actual_count:
                summary.note_count = actual_count
                summary.save(update_fields=['note_count'])

        if not summary:
            # Generate new summary
            week_end = week_start + timedelta(days=6)
            notes = MoodNote.objects.filter(
                user=request.user,
                is_deleted=False,
                created_at__date__gte=week_start,
                created_at__date__lte=week_end,
            )
            note_count = notes.count()
            if note_count == 0:
                return Response({'detail': 'No notes found for this week.'}, status=status.HTTP_404_NOT_FOUND)

            agg = notes.aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

            # Count activities
            activity_counts = {}
            for note in notes.values('metadata'):
                meta = note.get('metadata') or {}
                for act in meta.get('activities', []):
                    activity_counts[act] = activity_counts.get(act, 0) + 1
            top_activities = sorted(
                [{'name': k, 'count': v} for k, v in activity_counts.items()],
                key=lambda x: x['count'], reverse=True,
            )[:5]

            # Generate AI summary
            ai_summary = ''
            try:
                client = _get_openai_client()
                if client:
                    lang = request.headers.get('Accept-Language', 'zh-TW')
                    lang_map = {'zh-TW': 'Traditional Chinese', 'en': 'English', 'ja': 'Japanese'}
                    lang_name = lang_map.get(lang, 'Traditional Chinese')

                    # Collect diary content snippets (use search_text to avoid decryption overhead)
                    note_previews = list(notes.values_list('search_text', flat=True))
                    diary_snippets = '\n---\n'.join(
                        [(t[:200] if t else '') for t in note_previews if t]
                    )

                    content = (
                        f'You are a warm, professional mental health assistant. '
                        f'Generate a weekly mental health summary in {lang_name} based on the following data:\n\n'
                        f'Period: {week_start} to {week_end}\n'
                        f'Journal entries: {note_count}\n'
                        f'Average mood: {agg["avg_s"]:.2f} (-1 to 1 scale)\n'
                        f'Average stress: {agg["avg_st"]:.1f} (0-10 scale)\n'
                        f'Top activities: {top_activities}\n\n'
                        f'--- Diary excerpts ---\n{diary_snippets}\n\n'
                        f'Based on ALL the above data (diary content, mood, stress, activities), '
                        f'provide a comprehensive analysis with:\n'
                        f'1. Key emotional themes and patterns observed this week\n'
                        f'2. Specific observations tied to diary content\n'
                        f'3. Personalized suggestions based on what the user wrote\n'
                        f'Be warm, supportive, and specific (not generic).'
                    )

                    # Dynamic token limit: base 300 + 100 per diary entry, cap at 1500
                    max_tok = min(300 + note_count * 100, 1500)

                    resp = client.chat.completions.create(
                        model='gpt-4o-mini',
                        messages=[{'role': 'system', 'content': content}],
                        max_tokens=max_tok,
                        temperature=0.7,
                        timeout=30,
                    )
                    ai_summary = resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning('Weekly summary AI generation failed: %s', e)

            summary = WeeklySummary.objects.create(
                user=request.user,
                week_start=week_start,
                mood_avg=round(agg['avg_s'], 2) if agg['avg_s'] is not None else None,
                stress_avg=round(agg['avg_st'], 1) if agg['avg_st'] is not None else None,
                note_count=note_count,
                top_activities=top_activities,
                ai_summary=ai_summary,
            )

        # Check if PDF export requested
        if self._is_pdf_request(request):
            try:
                return self._generate_pdf_response(summary, request)
            except Exception as e:
                logger.error('Weekly summary PDF generation failed: %s', e, exc_info=True)
                return Response({'detail': 'PDF generation failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(WeeklySummarySerializer(summary).data)


class WeeklySummaryListView(generics.ListAPIView):
    serializer_class = WeeklySummarySerializer

    def get_queryset(self):
        return WeeklySummary.objects.filter(user=self.request.user)


# ===== Therapist Report Views =====

class TherapistReportCreateView(generics.CreateAPIView):
    serializer_class = TherapistReportSerializer

    def perform_create(self, serializer):
        user = self.request.user
        period_start = serializer.validated_data['period_start']
        period_end = serializer.validated_data['period_end']
        if period_end < period_start:
            raise exceptions.ValidationError({'detail': 'period_end must be >= period_start.'})

        notes = MoodNote.objects.filter(
            user=user, is_deleted=False,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
            sentiment_score__isnull=False,
        )

        # Build report data snapshot
        mood_data = list(notes.values('created_at', 'sentiment_score', 'stress_index'))
        for item in mood_data:
            item['created_at'] = item['created_at'].isoformat()

        agg = notes.aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

        # Recent assessments
        assessments = list(
            SelfAssessment.objects.filter(
                user=user,
                created_at__date__gte=period_start,
                created_at__date__lte=period_end,
            ).values('assessment_type', 'total_score', 'created_at')
        )
        for a in assessments:
            a['created_at'] = a['created_at'].isoformat()

        report_data = {
            'mood_trends': mood_data,
            'mood_avg': round(agg['avg_s'], 2) if agg['avg_s'] is not None else None,
            'stress_avg': round(agg['avg_st'], 1) if agg['avg_st'] is not None else None,
            'note_count': notes.count(),
            'assessments': assessments,
        }

        serializer.save(
            user=user,
            report_data=report_data,
            expires_at=timezone.now() + timedelta(days=30),
        )


class TherapistReportListView(generics.ListAPIView):
    serializer_class = TherapistReportSerializer

    def get_queryset(self):
        return TherapistReport.objects.filter(user=self.request.user)


class TherapistReportPublicView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [rest_framework.throttling.AnonRateThrottle]

    def get(self, request, token):
        try:
            report = TherapistReport.objects.get(token=token)
        except TherapistReport.DoesNotExist:
            return Response({'detail': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)
        if timezone.now() > report.expires_at:
            return Response({'detail': 'This report has expired.'}, status=status.HTTP_410_GONE)
        return Response(TherapistReportPublicSerializer(report).data)


# ===== Psycho Education Views =====

class PsychoArticleListView(generics.ListAPIView):
    serializer_class = PsychoArticleSerializer

    def get_queryset(self):
        qs = PsychoArticle.objects.filter(is_published=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class PsychoArticleDetailView(generics.RetrieveAPIView):
    serializer_class = PsychoArticleSerializer

    def get_queryset(self):
        return PsychoArticle.objects.filter(is_published=True)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        # Auto-create progress record when article is viewed
        article = self.get_object()
        UserLessonProgress.objects.get_or_create(
            user=request.user, article=article,
        )
        return response


# ===== Wellness Session Views =====

class WellnessSessionListCreateView(APIView):
    def get(self, request):
        sessions = WellnessSession.objects.filter(user=request.user)[:50]
        return Response(WellnessSessionSerializer(sessions, many=True).data)

    def post(self, request):
        serializer = WellnessSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ===== Course Views =====

class CourseListView(generics.ListAPIView):
    serializer_class = CourseListSerializer

    def get_queryset(self):
        from django.db.models import Count
        return Course.objects.filter(is_published=True).annotate(
            _lesson_count=Count('lessons', filter=Q(lessons__is_published=True)),
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        completed_ids = set(
            UserLessonProgress.objects.filter(
                user=self.request.user, completed_at__isnull=False,
            ).values_list('article_id', flat=True)
        )
        ctx['completed_ids'] = completed_ids
        return ctx


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer

    def get_queryset(self):
        from django.db.models import Count
        return Course.objects.filter(is_published=True).annotate(
            _lesson_count=Count('lessons', filter=Q(lessons__is_published=True)),
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        completed_ids = set(
            UserLessonProgress.objects.filter(
                user=self.request.user, completed_at__isnull=False,
            ).values_list('article_id', flat=True)
        )
        ctx['completed_ids'] = completed_ids
        return ctx


class LessonCompleteView(APIView):
    def post(self, request, pk):
        try:
            article = PsychoArticle.objects.get(pk=pk, is_published=True)
        except PsychoArticle.DoesNotExist:
            return Response({'detail': 'Article not found.'}, status=status.HTTP_404_NOT_FOUND)

        progress, created = UserLessonProgress.objects.get_or_create(
            user=request.user, article=article,
        )
        if not progress.completed_at:
            progress.completed_at = timezone.now()
            progress.save(update_fields=['completed_at'])
        return Response({'status': 'completed', 'completed_at': progress.completed_at})
