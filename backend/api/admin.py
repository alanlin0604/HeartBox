from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import (
    AIChatMessage, AIChatSession, AuditLog, Booking, Conversation,
    CounselorProfile, Course, CustomUser, DailySleep, DashboardLayout, Feedback,
    FriendComment, FriendRequest, Friendship, HealthMetric, JournalStreak,
    Message, MoodNote, NoteAttachment, Notification,
    NotificationPreference, PsychoArticle, PushSubscription, ReminderSettings,
    SelfAssessment, SharedAssessment, SharedNote, SharedWithFriend,
    SubscriptionPlan, Tag, TherapistReport, TimeSlot, TOTPDevice,
    UserAchievement, UserLessonProgress, UserMetric, UserSubscription,
    WeeklySummary, WellnessSession,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'token_version', 'created_at')
    list_per_page = 50
    fieldsets = UserAdmin.fieldsets + (
        ('Extra', {'fields': ('bio', 'avatar', 'token_version')}),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'color', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'name')
    readonly_fields = ('created_at',)
    list_per_page = 50


@admin.register(MoodNote)
class MoodNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'sentiment_score', 'stress_index', 'created_at')
    list_filter = ('created_at', 'stress_index')
    search_fields = ('user__username',)
    readonly_fields = ('encrypted_content', 'created_at', 'updated_at')
    list_per_page = 50


@admin.register(CounselorProfile)
class CounselorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'specialty', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'license_number', 'specialty')
    readonly_fields = ('created_at',)
    list_per_page = 50
    actions = ['approve_counselors', 'reject_counselors']

    @admin.action(description='審核通過所選諮商師')
    def approve_counselors(self, request, queryset):
        count = queryset.update(status='approved', reviewed_at=timezone.now())
        self.message_user(request, f'已通過 {count} 位諮商師的申請。')

    @admin.action(description='拒絕所選諮商師')
    def reject_counselors(self, request, queryset):
        count = queryset.update(status='rejected', reviewed_at=timezone.now())
        self.message_user(request, f'已拒絕 {count} 位諮商師的申請。')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'counselor', 'created_at', 'updated_at')
    search_fields = ('user__username', 'counselor__username')
    list_per_page = 50


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__username', 'content')
    list_per_page = 50


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'title')
    list_per_page = 50


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'sentiment_score', 'created_at')
    list_filter = ('role',)
    search_fields = ('content',)
    list_per_page = 50


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'achievement_id', 'unlocked_at')
    list_filter = ('achievement_id',)
    search_fields = ('user__username', 'achievement_id')
    list_per_page = 50


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'counselor', 'date', 'start_time', 'end_time', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'counselor__username')
    list_per_page = 50


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'counselor', 'day_of_week', 'start_time', 'end_time', 'is_active')
    list_filter = ('day_of_week', 'is_active')
    search_fields = ('counselor__username',)
    list_per_page = 50


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('user__username', 'title')
    list_per_page = 50


@admin.register(NoteAttachment)
class NoteAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'note', 'file_type', 'original_name', 'created_at')
    list_filter = ('file_type',)
    search_fields = ('original_name', 'note__user__username')
    list_per_page = 50


@admin.register(SharedNote)
class SharedNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'note', 'shared_with', 'is_anonymous', 'shared_at')
    list_filter = ('is_anonymous',)
    search_fields = ('note__user__username', 'shared_with__username')
    list_per_page = 50


@admin.register(SharedAssessment)
class SharedAssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'assessment', 'shared_with', 'shared_at')
    search_fields = ('assessment__user__username', 'shared_with__username')
    list_per_page = 50


@admin.register(SelfAssessment)
class SelfAssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'assessment_type', 'total_score', 'created_at')
    list_filter = ('assessment_type',)
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(WeeklySummary)
class WeeklySummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'week_start', 'mood_avg', 'stress_avg', 'note_count', 'created_at')
    list_filter = ('week_start',)
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(DailySleep)
class DailySleepAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'sleep_hours', 'sleep_quality', 'source')
    list_filter = ('sleep_quality', 'source')
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(HealthMetric)
class HealthMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'metric_type', 'value', 'source')
    list_filter = ('metric_type', 'source')
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(TherapistReport)
class TherapistReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'period_start', 'period_end', 'expires_at', 'created_at')
    search_fields = ('user__username', 'title')
    list_per_page = 50


@admin.register(PsychoArticle)
class PsychoArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_en', 'category', 'reading_time', 'is_published', 'order', 'created_at')
    list_filter = ('category', 'is_published')
    search_fields = ('title_en', 'title_zh', 'title_ja')
    list_per_page = 50


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_en', 'category', 'icon_emoji', 'is_published', 'order')
    list_filter = ('category', 'is_published')
    search_fields = ('title_en', 'title_zh', 'title_ja')
    list_per_page = 50


@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'article', 'started_at', 'completed_at')
    search_fields = ('user__username', 'article__title_en')
    list_per_page = 50


@admin.register(WellnessSession)
class WellnessSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_type', 'exercise_name', 'duration_seconds', 'completed_at')
    list_filter = ('session_type',)
    search_fields = ('user__username', 'exercise_name')
    list_per_page = 50


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('user__username', 'content')
    list_per_page = 50


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action', 'target_type', 'ip_address', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'action', 'target_type', 'target_id', 'ip_address', 'details', 'created_at')
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'confirmed', 'created_at')
    list_filter = ('confirmed',)
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tier', 'price', 'currency', 'is_active')
    list_filter = ('tier', 'is_active')
    list_per_page = 50


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'status', 'started_at', 'expires_at')
    list_filter = ('status', 'plan')
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'enabled')
    list_filter = ('notification_type', 'enabled')
    search_fields = ('user__username',)
    list_per_page = 50


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'endpoint', 'created_at')
    search_fields = ('user__username', 'endpoint')
    list_per_page = 50


@admin.register(ReminderSettings)
class ReminderSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'enabled', 'reminder_time', 'updated_at')
    list_filter = ('enabled',)
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(JournalStreak)
class JournalStreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_streak', 'longest_streak', 'total_entries', 'last_entry_date')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)
    list_per_page = 50


@admin.register(DashboardLayout)
class DashboardLayoutAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)
    list_per_page = 50


@admin.register(UserMetric)
class UserMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'metric_type', 'target_value', 'current_value', 'is_active', 'updated_at')
    list_filter = ('metric_type', 'is_active')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50


# ============ Friend System Admin ============


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'friend', 'created_at')
    search_fields = ('user__username', 'friend__username')
    readonly_fields = ('created_at',)
    list_per_page = 50


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50


@admin.register(SharedWithFriend)
class SharedWithFriendAdmin(admin.ModelAdmin):
    list_display = ('id', 'note', 'shared_by', 'shared_with', 'shared_at')
    search_fields = ('shared_by__username', 'shared_with__username')
    readonly_fields = ('shared_at',)
    list_per_page = 50


@admin.register(FriendComment)
class FriendCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'share', 'commenter', 'content_preview', 'created_at')
    search_fields = ('commenter__username', 'content')
    readonly_fields = ('created_at',)
    list_per_page = 50

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
