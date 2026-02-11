import mimetypes
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, viewsets, permissions, status, filters, exceptions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import (
    Booking, Conversation, CounselorProfile, Message, MoodNote,
    NoteAttachment, Notification, SharedNote, TimeSlot,
)
from .serializers import (
    AdminCounselorSerializer,
    AdminUserSerializer,
    BookingSerializer,
    ConversationSerializer,
    CounselorListSerializer,
    CounselorProfileSerializer,
    MessageSerializer,
    MoodNoteListSerializer,
    MoodNoteSerializer,
    NoteAttachmentSerializer,
    NotificationSerializer,
    SharedNoteSerializer,
    TimeSlotSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from .services.analytics import (
    get_mood_trends, get_mood_weather_correlation, get_frequent_tags,
    get_calendar_data, get_stress_by_tag,
)
from .services.alerts import check_mood_alerts
from .services.pdf_export import generate_notes_pdf
from .services.search import search_notes
from .throttles import LoginRateThrottle, PasswordResetRateThrottle, RegisterRateThrottle

User = get_user_model()


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
            raise exceptions.PermissionDenied('User not found')
        if int(token.get('token_version', -1)) != int(user.token_version):
            raise exceptions.PermissionDenied('Token no longer valid')
        return super().validate(attrs)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VersionedTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VersionedTokenRefreshSerializer


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            from django.conf import settings
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            reset_url = f'{frontend_url.rstrip("/")}/reset-password?uid={uid}&token={token}'
            send_mail(
                'HeartBox Password Reset',
                f'Use this link to reset your password: {reset_url}',
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@moodnotes.local'),
                [user.email],
                fail_silently=True,
            )
        return Response({'status': 'ok'})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        uid = request.data.get('uid') or ''
        token = request.data.get('token') or ''
        new_password = request.data.get('new_password') or ''
        if len(new_password) < 8:
            return Response({'error': 'Password too short'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save(update_fields=['password'])
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
            user.set_password(new_pw)
            user.save()
            return Response({'status': 'ok'})
        return super().update(request, *args, **kwargs)


class LogoutOtherDevicesView(APIView):
    def post(self, request):
        user = request.user
        user.token_version = user.token_version + 1
        user.save(update_fields=['token_version'])
        return Response(_issue_tokens(user))


class MoodNoteViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return MoodNoteListSerializer
        return MoodNoteSerializer

    def get_queryset(self):
        qs = MoodNote.objects.filter(user=self.request.user)
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

    def perform_create(self, serializer):
        note = serializer.save(user=self.request.user)
        from api.services.ai_engine import ai_engine
        plaintext = note.content
        if plaintext:
            result = ai_engine.analyze(plaintext)
            note.sentiment_score = result['sentiment_score']
            note.stress_index = result['stress_index']
            note.ai_feedback = result['ai_feedback']
            note.save(update_fields=['sentiment_score', 'stress_index', 'ai_feedback'])


class AnalyticsView(APIView):
    def get(self, request):
        period = request.query_params.get('period', 'week')
        lookback_days = int(request.query_params.get('lookback_days', 30))
        qs = MoodNote.objects.filter(user=request.user)

        return Response({
            'mood_trends': get_mood_trends(qs, period=period, lookback_days=lookback_days),
            'weather_correlation': get_mood_weather_correlation(qs, lookback_days=lookback_days),
            'frequent_tags': get_frequent_tags(qs, lookback_days=lookback_days),
            'stress_by_tag': get_stress_by_tag(qs, lookback_days=lookback_days),
        })


class CalendarView(APIView):
    def get(self, request):
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        qs = MoodNote.objects.filter(user=request.user)
        days = get_calendar_data(qs, year, month)
        return Response({'year': year, 'month': month, 'days': days})


class ExportPDFView(APIView):
    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        lang = request.query_params.get('lang', 'zh-TW')
        qs = MoodNote.objects.filter(user=request.user)
        buf = generate_notes_pdf(qs, date_from=date_from, date_to=date_to, user=request.user, lang=lang)
        return FileResponse(
            buf,
            as_attachment=True,
            filename=f'heartbox_{date_from or "all"}_{date_to or "now"}.pdf',
            content_type='application/pdf',
        )


class AlertsView(APIView):
    def get(self, request):
        qs = MoodNote.objects.filter(user=request.user)
        alerts = check_mood_alerts(qs)
        return Response({'alerts': alerts})


# ===== Counselor Views =====

class CounselorApplyView(generics.CreateAPIView):
    """User applies to become a counselor."""
    serializer_class = CounselorProfileSerializer

    def perform_create(self, serializer):
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
    """List all approved counselors (public for authenticated users)."""
    serializer_class = CounselorListSerializer
    queryset = CounselorProfile.objects.filter(status='approved')


# ===== Messaging Views =====

class ConversationListView(generics.ListAPIView):
    """List all conversations for the current user."""
    serializer_class = ConversationSerializer

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(user=user) | Q(counselor=user)
        ).select_related('user', 'counselor').prefetch_related('messages')


class ConversationCreateView(APIView):
    """Start a conversation with a counselor."""

    def post(self, request):
        counselor_id = request.data.get('counselor_id')
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return Response({'error': '找不到該諮商師'}, status=status.HTTP_404_NOT_FOUND)

        conv, created = Conversation.objects.get_or_create(
            user=request.user,
            counselor=profile.user,
        )
        return Response(ConversationSerializer(conv, context={'request': request}).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessageListView(APIView):
    """List messages in a conversation and send new messages."""

    def get(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return Response({'error': '對話不存在'}, status=status.HTTP_404_NOT_FOUND)

        # Mark unread messages as read
        conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        messages = conv.messages.all()
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return Response({'error': '對話不存在'}, status=status.HTTP_404_NOT_FOUND)

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': '訊息不可為空'}, status=status.HTTP_400_BAD_REQUEST)

        msg = Message.objects.create(conversation=conv, sender=request.user, content=content)
        conv.save()  # update updated_at

        # Create notification for the other party
        recipient_id = conv.counselor_id if conv.user_id == request.user.id else conv.user_id
        notif = Notification.objects.create(
            user_id=recipient_id,
            type='message',
            title='新訊息',
            message=content[:100],
            data={'conversation_id': conv.id, 'message_id': msg.id},
        )

        # Push via WebSocket
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
        except Exception:
            pass  # graceful degradation if channel layer not available

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


# ===== Admin Views =====

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        return Response({
            'total_users': User.objects.count(),
            'total_notes': MoodNote.objects.count(),
            'pending_counselors': CounselorProfile.objects.filter(status='pending').count(),
            'today_new_users': User.objects.filter(date_joined__date=today).count(),
            'today_new_notes': MoodNote.objects.filter(created_at__date=today).count(),
            'active_users': User.objects.filter(is_active=True).count(),
        })


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()


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
            return Response({'error': '找不到該諮商師'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action not in ('approve', 'reject'):
            return Response({'error': 'action 必須為 approve 或 reject'}, status=status.HTTP_400_BAD_REQUEST)

        profile.status = 'approved' if action == 'approve' else 'rejected'
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=['status', 'reviewed_at'])
        return Response(AdminCounselorSerializer(profile).data)


# ===== Notification Views =====

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer

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

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = {'image', 'audio'}

    def post(self, request, note_id):
        try:
            note = MoodNote.objects.get(id=note_id, user=request.user)
        except MoodNote.DoesNotExist:
            return Response({'error': '日記不存在'}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': '請上傳檔案'}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > self.MAX_FILE_SIZE:
            return Response({'error': '檔案大小不可超過 10MB'}, status=status.HTTP_400_BAD_REQUEST)

        mime_type = file.content_type or mimetypes.guess_type(file.name)[0] or ''
        file_type = mime_type.split('/')[0]
        if file_type not in self.ALLOWED_TYPES:
            return Response({'error': '只允許上傳圖片或音訊檔案'}, status=status.HTTP_400_BAD_REQUEST)

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
    """Get available slots for a counselor on a given date."""

    def get(self, request, counselor_id):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': '請提供 date 參數'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': '日期格式錯誤，請使用 YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        day_of_week = target_date.weekday()
        slots = TimeSlot.objects.filter(
            counselor_id=counselor_id,
            day_of_week=day_of_week,
            is_active=True,
        )

        # Exclude already booked slots
        booked = Booking.objects.filter(
            counselor_id=counselor_id,
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
        ).select_related('user', 'counselor').order_by('-created_at')
        return Response(BookingSerializer(bookings, many=True).data)


class BookingCreateView(APIView):
    def post(self, request):
        counselor_id = request.data.get('counselor_id')
        date_str = request.data.get('date')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        if not all([counselor_id, date_str, start_time, end_time]):
            return Response({'error': '請提供所有必填欄位'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for conflicts
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        conflict = Booking.objects.filter(
            counselor_id=counselor_id,
            date=target_date,
            start_time=start_time,
            status__in=['pending', 'confirmed'],
        ).exists()
        if conflict:
            return Response({'error': '該時段已被預約'}, status=status.HTTP_409_CONFLICT)

        booking = Booking.objects.create(
            user=request.user,
            counselor_id=counselor_id,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
        )

        # Notify counselor
        Notification.objects.create(
            user_id=counselor_id,
            type='booking',
            title='新預約',
            message=f'{request.user.username} 預約了 {date_str} {start_time}',
            data={'booking_id': booking.id},
        )

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingActionView(APIView):
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, counselor=request.user)
        except Booking.DoesNotExist:
            return Response({'error': '預約不存在'}, status=status.HTTP_404_NOT_FOUND)

        action_type = request.data.get('action')
        if action_type == 'confirm':
            booking.status = 'confirmed'
        elif action_type == 'cancel':
            booking.status = 'cancelled'
        elif action_type == 'complete':
            booking.status = 'completed'
        else:
            return Response({'error': 'action 必須為 confirm / cancel / complete'},
                            status=status.HTTP_400_BAD_REQUEST)
        booking.save(update_fields=['status'])

        # Notify user
        Notification.objects.create(
            user=booking.user,
            type='booking',
            title=f'預約{booking.get_status_display()}',
            message=f'您與 {booking.counselor.username} 的預約已{booking.get_status_display()}',
            data={'booking_id': booking.id},
        )

        return Response(BookingSerializer(booking).data)


# ===== Share Views =====

class ShareNoteView(APIView):
    def post(self, request, note_id):
        try:
            note = MoodNote.objects.get(id=note_id, user=request.user)
        except MoodNote.DoesNotExist:
            return Response({'error': '日記不存在'}, status=status.HTTP_404_NOT_FOUND)

        counselor_id = request.data.get('counselor_user_id') or request.data.get('counselor_id')
        is_anonymous = request.data.get('is_anonymous', False)

        if not counselor_id:
            return Response({'error': '請提供諮商師 ID'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the target is an approved counselor (accept either profile pk or user pk)
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            try:
                profile = CounselorProfile.objects.get(user_id=counselor_id, status='approved')
            except CounselorProfile.DoesNotExist:
                return Response({'error': '該諮商師不存在或未通過審核'}, status=status.HTTP_404_NOT_FOUND)

        counselor_user_id = profile.user_id

        shared, created = SharedNote.objects.get_or_create(
            note=note,
            shared_with_id=counselor_user_id,
            defaults={'is_anonymous': is_anonymous},
        )
        if not created:
            return Response({'error': '已分享過此日記'}, status=status.HTTP_409_CONFLICT)

        # Notify counselor
        author_name = '匿名使用者' if is_anonymous else request.user.username
        Notification.objects.create(
            user_id=counselor_user_id,
            type='share',
            title='收到日記分享',
            message=f'{author_name} 分享了一篇日記給您',
            data={'shared_note_id': shared.id, 'note_id': note.id},
        )

        return Response(SharedNoteSerializer(shared).data, status=status.HTTP_201_CREATED)


class SharedNotesReceivedView(generics.ListAPIView):
    serializer_class = SharedNoteSerializer

    def get_queryset(self):
        return SharedNote.objects.filter(shared_with=self.request.user).select_related('note', 'note__user')
