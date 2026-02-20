import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.html import strip_tags


class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    token_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.username


class MoodNote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    encrypted_content = models.TextField(help_text='AES-256 encrypted journal content')
    sentiment_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='-1.0 (negative) to 1.0 (positive)',
    )
    stress_index = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text='0 (calm) to 10 (extreme stress)',
    )
    ai_feedback = models.TextField(blank=True, default='')
    search_text = models.TextField(blank=True, default='', help_text='Plaintext index (first 500 chars) for DB-level search')
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text='weather, temperature, location, tags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='moodnote_user_created'),
            models.Index(fields=['user', 'sentiment_score'], name='moodnote_user_sentiment'),
            models.Index(fields=['user', 'search_text'], name='moodnote_user_search'),
            models.Index(fields=['user', 'is_deleted'], name='moodnote_user_deleted'),
        ]

    def __str__(self):
        return f'Note #{self.pk} by {self.user.username} ({self.created_at:%Y-%m-%d})'

    # --- Encryption helpers ---

    _raw_content = None

    def set_content(self, plaintext: str):
        """Stage plaintext content to be encrypted on save."""
        self._raw_content = plaintext

    def save(self, *args, **kwargs):
        if self._raw_content is not None:
            from api.services.encryption import encryption_service
            self.encrypted_content = encryption_service.encrypt(self._raw_content)
            self.search_text = strip_tags(self._raw_content)[:500]
            self._raw_content = None
        super().save(*args, **kwargs)

    @property
    def content(self) -> str:
        """Decrypt and return content."""
        if not self.encrypted_content:
            return ''
        from api.services.encryption import encryption_service
        return encryption_service.decrypt(self.encrypted_content)

    @property
    def content_preview(self) -> str:
        """First 100 chars for list views (from pre-stored plaintext, no decryption)."""
        full = self.search_text
        if len(full) <= 100:
            return full
        return full[:100] + '...'


class CounselorProfile(models.Model):
    """Counselor profile that requires admin verification."""

    STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '已通過'),
        ('rejected', '已拒絕'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='counselor_profile',
    )
    license_number = models.CharField(max_length=50, unique=True, help_text='諮商師執照號碼')
    display_name = models.CharField(max_length=50, blank=True, default='')
    specialty = models.CharField(max_length=200, help_text='專長領域')
    introduction = models.TextField(help_text='自我介紹')
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='TWD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} ({self.get_status_display()})'

    @property
    def is_approved(self):
        return self.status == 'approved'


class Conversation(models.Model):
    """A conversation thread between a user and a counselor."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_conversations',
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='counselor_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'counselor']
        indexes = [
            models.Index(fields=['-updated_at'], name='conv_updated_at'),
        ]

    def __str__(self):
        return f'{self.user.username} <-> {self.counselor.username}'


class Message(models.Model):
    """A message in a conversation."""

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('quote', 'Quote'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text')
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'is_read'], name='message_conv_read'),
            models.Index(fields=['sender', 'created_at'], name='message_sender_created'),
        ]

    def __str__(self):
        return f'{self.sender.username}: {self.content[:50]}'


class Notification(models.Model):
    TYPE_CHOICES = [
        ('message', '新訊息'),
        ('booking', '預約通知'),
        ('share', '日記分享'),
        ('system', '系統通知'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at'], name='notif_user_read'),
        ]

    def __str__(self):
        return f'{self.get_type_display()} → {self.user.username}: {self.title}'


class NoteAttachment(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', '圖片'),
        ('audio', '音訊'),
    ]

    note = models.ForeignKey(
        MoodNote,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(upload_to='attachments/%Y/%m/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    original_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.original_name} ({self.file_type})'


class TimeSlot(models.Model):
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='time_slots',
    )
    day_of_week = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text='0=Monday, 6=Sunday',
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['counselor', 'day_of_week', 'is_active'], name='timeslot_counselor_day'),
        ]

    def __str__(self):
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return f'{self.counselor.username} {days[self.day_of_week]} {self.start_time}-{self.end_time}'


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', '待確認'),
        ('confirmed', '已確認'),
        ('cancelled', '已取消'),
        ('completed', '已完成'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='counselor_bookings',
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['counselor', 'date', 'status'], name='booking_counselor_date'),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.counselor.username} {self.date} {self.start_time}'


class Feedback(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedbacks',
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    content = models.TextField(help_text='User feedback text')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.rating}★ ({self.created_at:%Y-%m-%d})'


class SharedNote(models.Model):
    note = models.ForeignKey(
        MoodNote,
        on_delete=models.CASCADE,
        related_name='shares',
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_shares',
    )
    is_anonymous = models.BooleanField(default=False)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-shared_at']
        unique_together = ['note', 'shared_with']
        indexes = [
            models.Index(fields=['shared_with', '-shared_at'], name='sharednote_user_date'),
        ]

    def __str__(self):
        return f'Note #{self.note_id} → {self.shared_with.username}'


class AIChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_chat_sessions',
    )
    title = models.CharField(max_length=100, default='New Chat')
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-updated_at']
        indexes = [
            models.Index(fields=['user', '-is_pinned', '-updated_at'], name='aichat_user_pin_upd'),
        ]

    def __str__(self):
        return f'AIChatSession #{self.pk} ({self.user.username}): {self.title}'


class AIChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'AI Assistant')]

    session = models.ForeignKey(
        AIChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    sentiment_score = models.FloatField(null=True, blank=True)
    stress_index = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at'], name='aichatmsg_session_created'),
        ]

    def __str__(self):
        return f'{self.role}: {self.content[:50]}'


class UserAchievement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievements',
    )
    achievement_id = models.CharField(max_length=50)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'achievement_id']
        ordering = ['-unlocked_at']

    def __str__(self):
        return f'{self.user.username} — {self.achievement_id}'


class AuditLog(models.Model):
    """Tracks important user actions for compliance and security auditing."""

    ACTION_CHOICES = [
        ('login', 'Login'),
        ('password_change', 'Password Change'),
        ('password_reset', 'Password Reset'),
        ('note_create', 'Note Created'),
        ('note_update', 'Note Updated'),
        ('note_delete', 'Note Deleted'),
        ('note_restore', 'Note Restored'),
        ('note_permanent_delete', 'Note Permanently Deleted'),
        ('account_delete', 'Account Deleted'),
        ('export_data', 'Data Exported'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, blank=True, default='')
    target_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='audit_user_created'),
            models.Index(fields=['action', '-created_at'], name='audit_action_created'),
        ]

    def __str__(self):
        return f'{self.user} — {self.action} @ {self.created_at:%Y-%m-%d %H:%M}'


class SelfAssessment(models.Model):
    TYPE_CHOICES = [('phq9', 'PHQ-9'), ('gad7', 'GAD-7')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assessments',
    )
    assessment_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    responses = models.JSONField()  # list of ints 0-3
    total_score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'assessment_type', '-created_at'], name='assess_user_type_date'),
        ]

    def __str__(self):
        return f'{self.user.username} {self.assessment_type} = {self.total_score} ({self.created_at:%Y-%m-%d})'


class WeeklySummary(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_summaries',
    )
    week_start = models.DateField()
    mood_avg = models.FloatField(null=True, blank=True)
    stress_avg = models.FloatField(null=True, blank=True)
    note_count = models.IntegerField(default=0)
    top_activities = models.JSONField(default=list, blank=True)
    ai_summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'week_start']
        ordering = ['-week_start']

    def __str__(self):
        return f'{self.user.username} week {self.week_start}'


class TherapistReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='therapist_reports',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=200)
    period_start = models.DateField()
    period_end = models.DateField()
    report_data = models.JSONField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} report: {self.title}'


class PsychoArticle(models.Model):
    CATEGORY_CHOICES = [
        ('cbt', 'CBT'),
        ('mindfulness', 'Mindfulness'),
        ('emotion', 'Emotion'),
        ('stress', 'Stress'),
        ('sleep', 'Sleep'),
    ]

    title_zh = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200)
    title_ja = models.CharField(max_length=200)
    content_zh = models.TextField()
    content_en = models.TextField()
    content_ja = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    reading_time = models.IntegerField(default=5)
    source = models.CharField(max_length=500, blank=True, default='')
    is_published = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    course = models.ForeignKey(
        'Course', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='lessons',
    )
    lesson_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title_en


class WellnessSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('breathing', 'Breathing'),
        ('meditation', 'Meditation'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wellness_sessions',
    )
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    exercise_name = models.CharField(max_length=100)
    duration_seconds = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        indexes = [
            models.Index(fields=['user', '-completed_at'], name='wellness_user_completed'),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.exercise_name} ({self.duration_seconds}s)'


class Course(models.Model):
    CATEGORY_CHOICES = [
        ('cbt', 'CBT'),
        ('stress', 'Stress'),
        ('emotion', 'Emotion'),
        ('mindfulness', 'Mindfulness'),
    ]

    title_zh = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200)
    title_ja = models.CharField(max_length=200)
    description_zh = models.TextField(blank=True, default='')
    description_en = models.TextField(blank=True, default='')
    description_ja = models.TextField(blank=True, default='')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    icon_emoji = models.CharField(max_length=10, default='')
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title_en


class UserLessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
    )
    article = models.ForeignKey(
        PsychoArticle,
        on_delete=models.CASCADE,
        related_name='user_progress',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'article']
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} — {self.article.title_en}'
