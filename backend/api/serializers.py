import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AIChatMessage, AIChatSession,
    Booking, Conversation, CounselorReview, Course, CounselorProfile,
    DailySleep, DashboardLayout, Feedback, FriendComment, FriendRequest,
    Friendship, Habit, HabitLog, HealthMetric, JournalStreak,
    Message, MoodNote, NoteAttachment, Notification, NotificationPreference,
    PostReaction, PublicPost, PushSubscription, PsychoArticle, ReminderSettings,
    SelfAssessment, SharedAssessment, SharedNote, SharedWithFriend, SubscriptionPlan, Tag,
    TherapistReport, TimeSlot, TOTPDevice,
    UserAchievement, UserLessonProgress, UserMetric, UserSubscription,
    WeeklySummary, WellnessSession,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    is_counselor = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'avatar', 'is_counselor', 'is_staff', 'timezone', 'onboarding_completed', 'email_verified', 'created_at', 'updated_at')
        read_only_fields = ('id', 'username', 'is_staff', 'email_verified', 'created_at', 'updated_at')

    def get_is_counselor(self, obj) -> bool:
        return hasattr(obj, 'counselor_profile') and obj.counselor_profile.is_approved


class TagSerializer(serializers.ModelSerializer):
    """Tag serializer for CRUD operations."""
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'created_at', 'note_count')
        read_only_fields = ('id', 'created_at')

    def get_note_count(self, obj) -> int:
        return obj.notes.filter(is_deleted=False).count()

    def validate_name(self, value):
        # Normalize tag name: strip whitespace, lowercase
        return value.strip().lower()


class MoodNoteSerializer(serializers.ModelSerializer):
    """Full serializer — write accepts plaintext `content`, read returns decrypted."""
    content = serializers.CharField(write_only=True)
    decrypted_content = serializers.CharField(source='content', read_only=True)
    attachments = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Tag.objects.none(), required=False
    )

    class Meta:
        model = MoodNote
        fields = (
            'id', 'content', 'decrypted_content',
            'sentiment_score', 'stress_index', 'ai_feedback',
            'is_pinned', 'metadata', 'tags', 'tag_ids', 'attachments', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'sentiment_score', 'stress_index', 'ai_feedback', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            self.fields['tag_ids'].queryset = Tag.objects.filter(user=request.user)

    def get_attachments(self, obj) -> list:
        return NoteAttachmentSerializer(obj.attachments.all(), many=True).data

    def create(self, validated_data):
        plaintext = validated_data.pop('content')
        tag_ids = validated_data.pop('tag_ids', [])
        note = MoodNote(**validated_data)
        note.set_content(plaintext)
        note.save()
        if tag_ids:
            note.tags.set(tag_ids)
        return note

    def update(self, instance, validated_data):
        plaintext = validated_data.pop('content', None)
        tag_ids = validated_data.pop('tag_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if plaintext is not None:
            instance.set_content(plaintext)
        instance.save()
        if tag_ids is not None:
            instance.tags.set(tag_ids)
        return instance


class MoodNoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — only decrypts first 100 chars."""
    content_preview = serializers.CharField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = MoodNote
        fields = (
            'id', 'content_preview',
            'sentiment_score', 'stress_index',
            'is_pinned', 'metadata', 'tags', 'created_at',
        )


# ===== Counselor =====

class CounselorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CounselorProfile
        fields = ('id', 'username', 'license_number', 'display_name', 'specialty', 'introduction',
                  'hourly_rate', 'currency', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'status', None) == 'approved':
            self.fields['license_number'].read_only = True


class CounselorListSerializer(serializers.ModelSerializer):
    """Public listing of approved counselors."""
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    avg_rating = serializers.FloatField(read_only=True, default=None)
    review_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = CounselorProfile
        fields = ('id', 'username', 'avatar', 'display_name', 'specialty', 'introduction', 'hourly_rate', 'currency', 'avg_rating', 'review_count')


class CounselorReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CounselorReview
        fields = ('id', 'username', 'rating', 'content', 'created_at')
        read_only_fields = ('id', 'username', 'created_at')


# ===== Messaging =====

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'sender_name', 'sender_avatar', 'content',
                  'message_type', 'metadata', 'is_read', 'created_at')
        read_only_fields = ('id', 'sender', 'sender_name', 'is_read', 'created_at')

    def get_sender_name(self, obj):
        profile = getattr(obj.sender, 'counselor_profile', None)
        if profile and profile.display_name:
            return profile.display_name
        return obj.sender.username


# ===== Admin =====

class AdminUserSerializer(serializers.ModelSerializer):
    is_counselor = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'bio',
            'is_staff', 'is_superuser', 'is_active', 'is_counselor',
            'date_joined', 'created_at',
        )
        read_only_fields = ('id', 'username', 'email', 'is_superuser', 'date_joined', 'created_at')

    def get_is_counselor(self, obj) -> bool:
        return hasattr(obj, 'counselor_profile') and obj.counselor_profile.is_approved


class AdminCounselorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CounselorProfile
        fields = (
            'id', 'username', 'email',
            'license_number', 'specialty', 'introduction',
            'status', 'reviewed_at', 'created_at',
        )
        read_only_fields = ('id', 'reviewed_at', 'created_at')


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'other_user', 'last_message', 'unread_count', 'updated_at')

    def get_other_user(self, obj) -> dict | None:
        request_user = self.context['request'].user
        other = obj.counselor if obj.user == request_user else obj.user
        avatar = None
        if getattr(other, 'avatar', None):
            request = self.context.get('request')
            avatar = request.build_absolute_uri(other.avatar.url) if request else other.avatar.url
        display_name = ''
        profile = getattr(other, 'counselor_profile', None)
        if profile and profile.display_name:
            display_name = profile.display_name
        return {'id': other.id, 'username': other.username, 'display_name': display_name, 'avatar': avatar}

    def get_last_message(self, obj) -> dict | None:
        # Prefetch ordered by -created_at, so first element is latest
        msgs = obj.messages.all()
        if msgs:
            msg = msgs[0]
            profile = getattr(msg.sender, 'counselor_profile', None)
            sender_name = profile.display_name if profile and profile.display_name else msg.sender.username
            return {'content': msg.content[:80], 'created_at': msg.created_at, 'sender_name': sender_name}
        return None

    def get_unread_count(self, obj) -> int:
        request_user = self.context['request'].user
        # Use prefetched messages to avoid N+1
        return sum(1 for m in obj.messages.all() if not m.is_read and m.sender_id != request_user.id)


# ===== Notification =====

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'type', 'title', 'message', 'data', 'is_read', 'created_at')
        read_only_fields = fields


# ===== Attachments =====

class NoteAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteAttachment
        fields = ('id', 'file', 'file_type', 'original_name', 'created_at')
        read_only_fields = ('id', 'created_at')


# ===== Schedule / Booking =====

class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ('id', 'day_of_week', 'start_time', 'end_time', 'is_active')
        read_only_fields = ('id',)

    def validate(self, data):
        start = data.get('start_time')
        end = data.get('end_time')
        if start and end and start >= end:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        return data


class BookingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    counselor_name = serializers.CharField(source='counselor.username', read_only=True)
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ('id', 'user', 'user_name', 'counselor', 'counselor_name',
                  'date', 'start_time', 'end_time', 'status',
                  'price', 'payment_note', 'created_at', 'has_review')
        read_only_fields = ('id', 'user', 'counselor', 'status', 'price', 'payment_note', 'created_at')

    def get_has_review(self, obj) -> bool:
        return hasattr(obj, 'review') and obj.review is not None


# ===== Feedback =====

class FeedbackSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Feedback
        fields = ('id', 'username', 'rating', 'content', 'created_at')
        read_only_fields = ('id', 'username', 'created_at')


# ===== Shared Notes =====

class SharedNoteSerializer(serializers.ModelSerializer):
    note_preview = serializers.CharField(source='note.content_preview', read_only=True)
    note_content = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    sentiment_score = serializers.FloatField(source='note.sentiment_score', read_only=True)
    stress_index = serializers.IntegerField(source='note.stress_index', read_only=True)
    note_created_at = serializers.DateTimeField(source='note.created_at', read_only=True)
    note_tags = serializers.SerializerMethodField()
    note_ai_feedback = serializers.CharField(source='note.ai_feedback', read_only=True)
    shared_with_username = serializers.CharField(source='shared_with.username', read_only=True)

    class Meta:
        model = SharedNote
        fields = ('id', 'note', 'author', 'note_preview', 'note_content',
                  'sentiment_score', 'stress_index', 'is_anonymous', 'shared_at',
                  'note_created_at', 'note_tags', 'note_ai_feedback', 'shared_with_username')
        read_only_fields = fields

    def get_author(self, obj) -> str:
        if obj.is_anonymous:
            return None
        return obj.note.user.username

    def get_note_content(self, obj) -> str:
        """Return full note content via decryption (never expose raw search_text)."""
        try:
            return obj.note.content or ''
        except Exception as e:
            logger.warning('SharedNote %s: decryption failed: %s', obj.pk, e)
            return ''

    def get_note_tags(self, obj) -> list:
        meta = obj.note.metadata or {}
        return meta.get('tags', [])


# ===== AI Chat =====

class AIChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatMessage
        fields = ('id', 'role', 'content', 'sentiment_score', 'stress_index', 'created_at')
        read_only_fields = fields


class AIChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = AIChatSession
        fields = ('id', 'title', 'is_active', 'is_pinned', 'message_count', 'last_message_preview', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_message_count(self, obj):
        # Use annotation if available, otherwise fallback to query
        if hasattr(obj, '_message_count'):
            return obj._message_count
        return obj.messages.count()

    def get_last_message_preview(self, obj):
        # Use annotation if available, otherwise fallback to query
        if hasattr(obj, '_last_message_preview'):
            return obj._last_message_preview
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return last_msg.content[:80]
        return None


class UserAchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAchievement
        fields = ('achievement_id', 'unlocked_at')
        read_only_fields = fields


# ===== Wellness Features =====

class SelfAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SelfAssessment
        fields = ('id', 'assessment_type', 'responses', 'total_score', 'created_at')
        read_only_fields = ('id', 'total_score', 'created_at')

    def validate(self, data):
        atype = data.get('assessment_type')
        responses = data.get('responses')
        expected_len = 9 if atype == 'phq9' else 7
        if not isinstance(responses, list) or len(responses) != expected_len:
            raise serializers.ValidationError({
                'responses': f'Must be a list of {expected_len} integers.'
            })
        for val in responses:
            if not isinstance(val, int) or val < 0 or val > 3:
                raise serializers.ValidationError({
                    'responses': 'Each response must be an integer from 0 to 3.'
                })
        return data

    def create(self, validated_data):
        validated_data['total_score'] = sum(validated_data.get('responses', []))
        return super().create(validated_data)


class SharedAssessmentSerializer(serializers.ModelSerializer):
    assessment_type = serializers.CharField(source='assessment.assessment_type', read_only=True)
    responses = serializers.JSONField(source='assessment.responses', read_only=True)
    total_score = serializers.IntegerField(source='assessment.total_score', read_only=True)
    assessment_date = serializers.DateTimeField(source='assessment.created_at', read_only=True)
    username = serializers.CharField(source='assessment.user.username', read_only=True)

    class Meta:
        model = SharedAssessment
        fields = ('id', 'assessment', 'assessment_type', 'responses', 'total_score',
                  'assessment_date', 'username', 'shared_at')
        read_only_fields = fields


class WeeklySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklySummary
        fields = ('id', 'week_start', 'mood_avg', 'stress_avg', 'note_count',
                  'top_activities', 'ai_summary', 'created_at')
        read_only_fields = fields


class DailySleepSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySleep
        fields = ('id', 'date', 'sleep_hours', 'sleep_quality',
                  'bedtime', 'wake_time', 'deep_sleep_minutes',
                  'light_sleep_minutes', 'rem_sleep_minutes', 'source',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_sleep_hours(self, value):
        if value < 0 or value > 24:
            raise serializers.ValidationError('Sleep hours must be between 0 and 24.')
        return value

    def validate_sleep_quality(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Sleep quality must be between 1 and 5.')
        return value


class DailySleepDetailSerializer(serializers.ModelSerializer):
    """擴充的睡眠記錄 Serializer（含分析欄位）"""
    quality_score = serializers.SerializerMethodField()
    sleep_pattern = serializers.SerializerMethodField()

    class Meta:
        model = DailySleep
        fields = ('id', 'date', 'sleep_hours', 'sleep_quality',
                  'bedtime', 'wake_time', 'deep_sleep_minutes',
                  'light_sleep_minutes', 'rem_sleep_minutes', 'source',
                  'quality_score', 'sleep_pattern', 'created_at', 'updated_at')
        read_only_fields = ('id', 'quality_score', 'sleep_pattern', 'created_at', 'updated_at')

    def get_quality_score(self, obj):
        """計算睡眠品質分數 (0-100)"""
        from .services.sleep_analysis import calculate_quality_score
        return calculate_quality_score(
            obj.sleep_hours,
            obj.deep_sleep_minutes,
            obj.light_sleep_minutes,
            obj.rem_sleep_minutes
        )

    def get_sleep_pattern(self, obj):
        """識別睡眠模式"""
        from .services.sleep_analysis import identify_sleep_pattern
        return identify_sleep_pattern(obj.bedtime, obj.wake_time, obj.user, days=7)


class HealthMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthMetric
        fields = ('id', 'date', 'metric_type', 'value', 'source',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_metric_type(self, value):
        valid_types = [c[0] for c in HealthMetric.METRIC_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f'Invalid metric type. Choose from: {", ".join(valid_types)}')
        return value


class HealthSyncSerializer(serializers.Serializer):
    """Accepts a batch of health metrics + sleep data for sync."""
    metrics = HealthMetricSerializer(many=True, required=False, default=[])
    sleep = DailySleepSerializer(many=True, required=False, default=[])


class TherapistReportSerializer(serializers.ModelSerializer):
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = TherapistReport
        fields = ('id', 'token', 'title', 'period_start', 'period_end',
                  'report_data', 'expires_at', 'share_url', 'created_at')
        read_only_fields = ('id', 'token', 'report_data', 'expires_at', 'share_url', 'created_at')

    def get_share_url(self, obj) -> str:
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/reports/public/{obj.token}/')
        return f'/api/reports/public/{obj.token}/'


class TherapistReportPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TherapistReport
        fields = ('title', 'period_start', 'period_end', 'report_data', 'created_at')


class PsychoArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychoArticle
        fields = ('id', 'title_zh', 'title_en', 'title_ja',
                  'content_zh', 'content_en', 'content_ja',
                  'category', 'reading_time', 'source', 'order',
                  'course', 'lesson_order', 'created_at')


class WellnessSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessSession
        fields = ('id', 'session_type', 'exercise_name', 'duration_seconds', 'completed_at')
        read_only_fields = ('id', 'completed_at')


class CourseListSerializer(serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'title_zh', 'title_en', 'title_ja',
                  'description_zh', 'description_en', 'description_ja',
                  'category', 'icon_emoji', 'order',
                  'lesson_count', 'completed_count', 'progress_pct')

    def get_lesson_count(self, obj) -> int:
        if hasattr(obj, '_lesson_count'):
            return obj._lesson_count
        return obj.lessons.filter(is_published=True).count()

    def get_completed_count(self, obj) -> int:
        completed_ids = self.context.get('completed_ids', set())
        if completed_ids is not None and hasattr(obj, '_lesson_count'):
            lesson_ids = set(obj.lessons.filter(is_published=True).values_list('id', flat=True))
            return len(lesson_ids & completed_ids)
        request = self.context.get('request')
        if not request:
            return 0
        return UserLessonProgress.objects.filter(
            user=request.user, article__course=obj, completed_at__isnull=False,
        ).count()

    def get_progress_pct(self, obj) -> float:
        total = self.get_lesson_count(obj)
        if total == 0:
            return 0
        completed = self.get_completed_count(obj)
        return round(completed / total * 100)


class CourseLessonSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = PsychoArticle
        fields = ('id', 'title_zh', 'title_en', 'title_ja',
                  'category', 'reading_time', 'lesson_order', 'is_completed')

    def get_is_completed(self, obj):
        completed_ids = self.context.get('completed_ids')
        if completed_ids is not None:
            return obj.id in completed_ids
        request = self.context.get('request')
        if not request:
            return False
        return UserLessonProgress.objects.filter(
            user=request.user, article=obj, completed_at__isnull=False,
        ).exists()


class CourseDetailSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'title_zh', 'title_en', 'title_ja',
                  'description_zh', 'description_en', 'description_ja',
                  'category', 'icon_emoji', 'order',
                  'lessons', 'lesson_count', 'completed_count', 'progress_pct')

    def get_lessons(self, obj) -> list:
        lessons = obj.lessons.filter(is_published=True).order_by('lesson_order')
        return CourseLessonSerializer(lessons, many=True, context=self.context).data

    def get_lesson_count(self, obj) -> int:
        if hasattr(obj, '_lesson_count'):
            return obj._lesson_count
        return obj.lessons.filter(is_published=True).count()

    def get_completed_count(self, obj) -> int:
        completed_ids = self.context.get('completed_ids', set())
        if completed_ids is not None and hasattr(obj, '_lesson_count'):
            lesson_ids = set(obj.lessons.filter(is_published=True).values_list('id', flat=True))
            return len(lesson_ids & completed_ids)
        request = self.context.get('request')
        if not request:
            return 0
        return UserLessonProgress.objects.filter(
            user=request.user, article__course=obj, completed_at__isnull=False,
        ).count()

    def get_progress_pct(self, obj) -> float:
        total = self.get_lesson_count(obj)
        if total == 0:
            return 0
        completed = self.get_completed_count(obj)
        return round(completed / total * 100)


# ===== 2FA / TOTP =====

class TOTPSetupSerializer(serializers.Serializer):
    secret = serializers.CharField(read_only=True)
    otpauth_uri = serializers.CharField(read_only=True)
    qr_code = serializers.CharField(read_only=True)


class TOTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


# ===== Subscription =====

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'name', 'tier', 'price', 'currency', 'features', 'is_active')


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_tier = serializers.CharField(source='plan.tier', read_only=True)

    class Meta:
        model = UserSubscription
        fields = ('id', 'plan', 'plan_name', 'plan_tier', 'status', 'started_at', 'expires_at')
        read_only_fields = ('id', 'status', 'started_at', 'expires_at')


# ===== Notification Preferences =====

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ('notification_type', 'enabled')


class PushSubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())


class ReminderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderSettings
        fields = ('enabled', 'reminder_time', 'updated_at')
        read_only_fields = ('updated_at',)


class JournalStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalStreak
        fields = ('current_streak', 'longest_streak', 'last_entry_date', 'total_entries', 'updated_at')
        read_only_fields = fields


# ===== Habit Tracking =====

class HabitSerializer(serializers.ModelSerializer):
    streak = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    checked_today = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id', 'name', 'description', 'category', 'color', 'icon',
            'target_frequency', 'target_count', 'is_active',
            'reminder_enabled', 'reminder_time',
            'created_at', 'updated_at', 'streak', 'completion_rate',
            'checked_today',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'streak', 'completion_rate', 'checked_today',
        ]

    def get_checked_today(self, obj) -> bool:
        """True if a HabitLog exists for today — used by the frontend to show
        the post-check-in 'done' state without needing the dashboard refetch."""
        from django.utils import timezone
        return HabitLog.objects.filter(habit=obj, date=timezone.now().date()).exists()

    def get_streak(self, obj) -> int:
        """Calculate current consecutive days streak."""
        from datetime import timedelta
        from django.utils import timezone

        today = timezone.now().date()
        streak = 0
        check_date = today

        while True:
            if HabitLog.objects.filter(habit=obj, date=check_date).exists():
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
            if streak > 365:
                break

        return streak

    def get_completion_rate(self, obj) -> float:
        """Calculate completion rate for last 30 days."""
        from datetime import timedelta
        from django.utils import timezone

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        total_days = 30
        completed_days = HabitLog.objects.filter(
            habit=obj,
            date__gte=start_date,
            date__lte=end_date
        ).count()

        return round((completed_days / total_days) * 100, 1) if total_days > 0 else 0.0


class HabitLogSerializer(serializers.ModelSerializer):
    habit_name = serializers.CharField(source='habit.name', read_only=True)

    class Meta:
        model = HabitLog
        fields = ['id', 'habit', 'habit_name', 'completed_at', 'date', 'note']
        read_only_fields = ['id', 'completed_at', 'date']

    def create(self, validated_data):
        from django.utils import timezone
        validated_data['date'] = timezone.now().date()
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DashboardLayoutSerializer(serializers.ModelSerializer):
    """Serializer for user's dashboard layout configuration."""

    class Meta:
        model = DashboardLayout
        fields = ['layout_config', 'updated_at']
        read_only_fields = ['updated_at']

    def validate_layout_config(self, value):
        """Validate the JSON structure of layout_config."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("layout_config must be a dictionary")

        if 'widgets' not in value:
            raise serializers.ValidationError("Missing 'widgets' key in layout_config")

        if not isinstance(value['widgets'], list):
            raise serializers.ValidationError("'widgets' must be a list")

        # Validate each widget has required fields
        required_fields = ['id', 'x', 'y', 'w', 'h', 'enabled']
        for idx, widget in enumerate(value['widgets']):
            if not isinstance(widget, dict):
                raise serializers.ValidationError(f"Widget at index {idx} must be a dictionary")

            for field in required_fields:
                if field not in widget:
                    raise serializers.ValidationError(f"Widget at index {idx} missing required field: {field}")

            # Validate data types
            if not isinstance(widget['id'], str):
                raise serializers.ValidationError(f"Widget {idx}: 'id' must be a string")
            if not isinstance(widget['enabled'], bool):
                raise serializers.ValidationError(f"Widget {idx}: 'enabled' must be a boolean")
            for pos_field in ['x', 'y', 'w', 'h']:
                if not isinstance(widget[pos_field], (int, float)):
                    raise serializers.ValidationError(f"Widget {idx}: '{pos_field}' must be a number")

        return value


class UserMetricSerializer(serializers.ModelSerializer):
    """Serializer for user's custom metric tracking."""
    progress = serializers.SerializerMethodField()

    class Meta:
        model = UserMetric
        fields = ['id', 'metric_type', 'target_value', 'current_value', 'progress', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'current_value', 'progress', 'created_at', 'updated_at']

    def get_progress(self, obj):
        """Calculate progress percentage."""
        if obj.target_value == 0:
            return 0.0
        return round((obj.current_value / obj.target_value) * 100, 1)

    def validate_target_value(self, value):
        """Ensure target value is positive."""
        if value <= 0:
            raise serializers.ValidationError("Target value must be greater than 0")
        return value


# ============ Friend System Serializers ============


class FriendshipSerializer(serializers.ModelSerializer):
    """Serializer for friendship relationships."""
    user_id = serializers.IntegerField(source='friend.id', read_only=True)
    username = serializers.CharField(source='friend.username', read_only=True)
    email = serializers.EmailField(source='friend.email', read_only=True)
    avatar = serializers.ImageField(source='friend.avatar', read_only=True)
    streak_days = serializers.SerializerMethodField()
    total_entries = serializers.SerializerMethodField()
    friendship_since = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'user_id', 'username', 'email', 'avatar', 'streak_days', 'total_entries', 'friendship_since']
        read_only_fields = ['id', 'friendship_since']

    def get_streak_days(self, obj) -> int:
        """Get friend's current streak."""
        try:
            streak = JournalStreak.objects.get(user=obj.friend)
            return streak.current_streak
        except JournalStreak.DoesNotExist:
            return 0

    def get_total_entries(self, obj) -> int:
        """Get friend's total journal entries."""
        return MoodNote.objects.filter(user=obj.friend, is_deleted=False).count()


class FriendRequestSerializer(serializers.ModelSerializer):
    """Serializer for friend requests."""
    from_user_id = serializers.IntegerField(source='from_user.id', read_only=True)
    from_user_username = serializers.CharField(source='from_user.username', read_only=True)
    from_user_avatar = serializers.ImageField(source='from_user.avatar', read_only=True)
    to_user_id = serializers.IntegerField(source='to_user.id', read_only=True)
    to_user_username = serializers.CharField(source='to_user.username', read_only=True)

    class Meta:
        model = FriendRequest
        fields = [
            'id', 'from_user_id', 'from_user_username', 'from_user_avatar',
            'to_user_id', 'to_user_username', 'status', 'message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class SharedWithFriendSerializer(serializers.ModelSerializer):
    """Serializer for shared notes with friends."""
    shared_by_id = serializers.IntegerField(source='shared_by.id', read_only=True)
    shared_by_username = serializers.CharField(source='shared_by.username', read_only=True)
    shared_by_avatar = serializers.ImageField(source='shared_by.avatar', read_only=True)
    content_preview = serializers.SerializerMethodField()
    sentiment_score = serializers.FloatField(source='note.sentiment_score', read_only=True)
    created_at = serializers.DateTimeField(source='note.created_at', read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = SharedWithFriend
        fields = [
            'id', 'note', 'shared_by_id', 'shared_by_username', 'shared_by_avatar',
            'shared_at', 'content_preview', 'sentiment_score', 'created_at', 'comment_count'
        ]
        read_only_fields = ['id', 'shared_at']

    def get_content_preview(self, obj) -> str:
        """Return first 100 chars of note content."""
        content = obj.note.search_text
        if len(content) > 100:
            return content[:100] + '...'
        return content

    def get_comment_count(self, obj) -> int:
        """Return comment count for this share."""
        return obj.comments.count()


class SharedWithFriendDetailSerializer(SharedWithFriendSerializer):
    """Detailed serializer with full content."""
    decrypted_content = serializers.CharField(source='note.content', read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta(SharedWithFriendSerializer.Meta):
        fields = SharedWithFriendSerializer.Meta.fields + ['decrypted_content', 'tags']

    def get_tags(self, obj) -> list:
        """Return tags for the note."""
        return TagSerializer(obj.note.tags.all(), many=True).data


class FriendCommentSerializer(serializers.ModelSerializer):
    """Serializer for comments on shared notes."""
    commenter_id = serializers.IntegerField(source='commenter.id', read_only=True)
    commenter_username = serializers.CharField(source='commenter.username', read_only=True)
    commenter_avatar = serializers.ImageField(source='commenter.avatar', read_only=True)

    class Meta:
        model = FriendComment
        fields = ['id', 'commenter_id', 'commenter_username', 'commenter_avatar', 'content', 'created_at']
        read_only_fields = ['id', 'commenter_id', 'created_at']


class UserSearchSerializer(serializers.ModelSerializer):
    """Serializer for user search results."""
    is_friend = serializers.SerializerMethodField()
    has_pending_request = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar', 'bio', 'is_friend', 'has_pending_request']
        read_only_fields = ['id', 'username', 'email', 'avatar', 'bio']

    def get_is_friend(self, obj):
        """Check if already friends with current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Friendship.objects.filter(user=request.user, friend=obj).exists()
        return False

    def get_has_pending_request(self, obj):
        """Check if there's a pending friend request."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FriendRequest.objects.filter(
                from_user=request.user, to_user=obj, status='pending'
            ).exists()
        return False


class PostReactionSerializer(serializers.ModelSerializer):
    """Serializer for post reactions."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PostReaction
        fields = ['id', 'reaction_type', 'username', 'created_at']
        read_only_fields = ['id', 'username', 'created_at']


class PublicPostSerializer(serializers.ModelSerializer):
    """Serializer for public community posts."""
    reaction_counts = serializers.SerializerMethodField()
    user_reacted = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = PublicPost
        fields = [
            'id', 'content', 'sentiment_score', 'category',
            'created_at', 'reaction_counts', 'user_reacted', 'is_owner'
        ]
        read_only_fields = ['id', 'sentiment_score', 'category', 'created_at']

    def get_reaction_counts(self, obj) -> dict:
        """Count reactions by type."""
        from django.db.models import Count
        reactions = obj.reactions.values('reaction_type').annotate(count=Count('id'))
        return {r['reaction_type']: r['count'] for r in reactions}

    def get_user_reacted(self, obj) -> list:
        """List of reaction types current user has given."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return list(
                obj.reactions.filter(user=request.user).values_list('reaction_type', flat=True)
            )
        return []

    def get_is_owner(self, obj) -> bool:
        """Check if current user owns this post."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id
        return False


class PublicPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating public posts."""
    class Meta:
        model = PublicPost
        fields = ['content', 'category']

    def validate_content(self, value):
        """Validate content length."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Content must be at least 10 characters.')
        if len(value) > 5000:
            raise serializers.ValidationError('Content must not exceed 5000 characters.')
        return value.strip()
