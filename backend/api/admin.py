from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import AIChatMessage, AIChatSession, Conversation, CounselorProfile, CustomUser, Message, MoodNote, UserAchievement


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'token_version', 'created_at')
    list_per_page = 50
    fieldsets = UserAdmin.fieldsets + (
        ('Extra', {'fields': ('bio', 'avatar', 'token_version')}),
    )


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
