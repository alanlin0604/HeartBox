import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.html import strip_tags

from api.services.encryption import EncryptedTextField


class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    token_version = models.PositiveIntegerField(default=0)
    timezone = models.CharField(max_length=50, default='Asia/Taipei')
    onboarding_completed = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    # Captured at signup so we can prove (per GDPR Art. 7 / 台灣 PDPA §7)
    # exactly when this user agreed to which version of ToS / Privacy.
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    # Self-declared "I am at least 13". Store as a boolean rather than DOB
    # both to minimise PII and to mirror what we actually need (age-gate
    # only — we do not personalise on date of birth).
    age_confirmed_13_plus = models.BooleanField(default=False)
    # 2026-06-02: advisor feedback — split consent into 3 distinct gates
    # so users can decline AI-training use of their data without losing
    # the rest of the app, and minors (13-17) need parental sign-off.
    # `consent_ai_training_at` is the timestamp the user opted in (or
    # explicitly declined → null). `age_band` is one of 18_plus / 13_17 /
    # under_13. Under-13 fails registration. 13-17 requires a guardian
    # email + email-link confirmation before the account unlocks.
    AGE_BAND_CHOICES = (
        ('18_plus', 'Adult (18+)'),
        ('13_17',   'Minor (13-17, guardian required)'),
        ('under_13', 'Under 13 (not allowed)'),
    )
    consent_ai_training = models.BooleanField(default=False)
    consent_ai_training_at = models.DateTimeField(null=True, blank=True)
    age_band = models.CharField(max_length=10, choices=AGE_BAND_CHOICES, blank=True, default='')
    guardian_email = models.EmailField(blank=True, default='')
    guardian_consent_token = models.CharField(max_length=64, blank=True, default='')
    guardian_consent_at = models.DateTimeField(null=True, blank=True)
    # 30-day grace period when the user requests account deletion. Filled
    # by DeleteAccountView; a Celery beat task hard-deletes the row after
    # this date. Null means "active account, no pending deletion".
    deletion_scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.username


class Tag(models.Model):
    """User-defined tags for organizing notes."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tags',
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#6366f1', help_text='Hex color code')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'name'], name='tag_user_name'),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.name}'


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
    # Fernet-encrypted at rest (transparent via EncryptedTextField).
    # Plaintext on Python access, ciphertext in the DB cell. AI-derived
    # paraphrase of journal sentiment + advice — protected against DB dumps
    # / DBA inspection / BAK leakage. See [docs/phase0b-status.md].
    ai_feedback = EncryptedTextField(blank=True, default='')
    search_text = models.TextField(blank=True, default='', help_text='Plaintext index (first 500 chars) for DB-level search')
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text='weather, temperature, location, legacy tags')
    tags = models.ManyToManyField(Tag, blank=True, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # `-id` tie-break: two notes created in the same second (or on
        # backfill where created_at gets bulk-set) otherwise reorder
        # arbitrarily across pagination pages — page 1 and page 2 can
        # then both contain the same row.
        ordering = ['-is_pinned', '-created_at', '-id']
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='counselor_status_created'),
        ]

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
    # Private DMs — Fernet-encrypted at rest (same protection as MoodNote).
    content = EncryptedTextField()
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
        ('friend_request', '好友請求'),
        ('friend_accepted', '好友已接受'),
        ('friend_share', '好友分享日記'),
        ('friend_comment', '好友留言'),
        ('post_reaction', '社群貼文有人回應'),
        ('habit_reminder', '習慣打卡提醒'),
        ('achievement', '成就解鎖'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    # Notification bodies often quote user content (e.g. "Alice 對你說：感覺很...");
    # encrypt at rest so a DB dump can't reconstruct social-graph + content.
    message = EncryptedTextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at'], name='notif_user_read'),
        ]

    def __str__(self):
        # title intentionally — message is encrypted and decryption shouldn't
        # be triggered by repr / admin list display.
        return f'<Notification id={self.pk}>'


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


class CounselorReview(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_reviews',
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_reviews',
    )
    booking = models.OneToOneField(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    content = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['counselor', 'created_at'], name='review_counselor_date'),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.counselor.username} ({self.rating}/5)'


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
    # Fernet-encrypted at rest. Both user messages and assistant replies
    # are highly sensitive (it's a counselling-style conversation about
    # mental health). Transparent via EncryptedTextField — readers see
    # plaintext, the DB cell holds ciphertext.
    content = EncryptedTextField()
    sentiment_score = models.FloatField(null=True, blank=True)
    stress_index = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at'], name='aichatmsg_session_created'),
        ]

    def __str__(self):
        # ``content`` is decrypted on access; slicing decrypted str is safe.
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
    # BigInt because every PK in this schema is BigAutoField (8-byte); a
    # signed 32-bit target_id would silently overflow once any referenced
    # row's PK exceeds 2.1B.
    target_id = models.BigIntegerField(null=True, blank=True)
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


class SharedAssessment(models.Model):
    assessment = models.ForeignKey(
        SelfAssessment,
        on_delete=models.CASCADE,
        related_name='shares',
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_assessments',
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['assessment', 'shared_with']
        ordering = ['-shared_at']

    def __str__(self):
        return f'Assessment #{self.assessment_id} → {self.shared_with.username}'


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
    # Fernet-encrypted at rest. Week-level AI summary derived from journals
    # — themes, suggestions, paraphrase of the user's emotional arc. Same
    # protection rationale as MoodNote.ai_feedback.
    ai_summary = EncryptedTextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'week_start']
        ordering = ['-week_start']
        indexes = [
            models.Index(fields=['user', 'week_start'], name='weeklysummary_user_week'),
        ]

    def __str__(self):
        return f'{self.user.username} week {self.week_start}'


class DailySleep(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sleep_records',
    )
    date = models.DateField()
    sleep_hours = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    sleep_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    bedtime = models.DateTimeField(null=True, blank=True)
    wake_time = models.DateTimeField(null=True, blank=True)
    deep_sleep_minutes = models.IntegerField(null=True, blank=True)
    light_sleep_minutes = models.IntegerField(null=True, blank=True)
    rem_sleep_minutes = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=50, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'{self.user.username} {self.date} — {self.sleep_hours}h'


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
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    reading_time = models.IntegerField(default=5)
    source = models.CharField(max_length=500, blank=True, default='')
    is_published = models.BooleanField(default=True, db_index=True)
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
        indexes = [
            # Hot query: PsychoArticleListView filters published + category + orders by order.
            models.Index(fields=['is_published', 'category', 'order'], name='article_pub_cat_order'),
        ]

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


class TOTPDevice(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='totp_device',
    )
    secret = models.CharField(max_length=64)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'TOTP for {self.user.username} ({"confirmed" if self.confirmed else "pending"})'


class SubscriptionPlan(models.Model):
    TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('counselor', 'Counselor'),
    ]

    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='TWD')
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f'{self.name} ({self.tier})'


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscribers',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} — {self.plan.name} ({self.status})'


class NotificationPreference(models.Model):
    TYPE_CHOICES = [
        ('message', 'Message'),
        ('booking', 'Booking'),
        ('share', 'Share'),
        ('weekly_report', 'Weekly Report'),
        ('achievement', 'Achievement'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'notification_type']

    def __str__(self):
        return f'{self.user.username} — {self.notification_type}: {"on" if self.enabled else "off"}'


class HealthMetric(models.Model):
    METRIC_CHOICES = [
        ('steps', 'Steps'),
        ('heart_rate', 'Heart Rate'),
        ('hrv', 'Heart Rate Variability'),
        ('active_calories', 'Active Calories'),
        ('exercise_minutes', 'Exercise Minutes'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_metrics',
    )
    date = models.DateField()
    metric_type = models.CharField(max_length=30, choices=METRIC_CHOICES)
    value = models.FloatField()
    source = models.CharField(max_length=50, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date', 'metric_type']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'date'], name='healthmetric_user_date'),
            models.Index(fields=['user', 'metric_type', '-date'], name='healthmetric_user_type_date'),
        ]

    def __str__(self):
        return f'{self.user.username} {self.date} — {self.metric_type}: {self.value}'


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Push for {self.user.username} ({self.endpoint[:50]}...)'


class ReminderSettings(models.Model):
    """User's daily reminder preferences for journaling."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reminder_settings',
    )
    enabled = models.BooleanField(default=True)
    reminder_time = models.TimeField(default='20:00', help_text='Local time for daily reminder')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Reminder Settings'

    def __str__(self):
        status = 'enabled' if self.enabled else 'disabled'
        return f'{self.user.username} — {self.reminder_time} ({status})'


class JournalStreak(models.Model):
    """Tracks user's journaling streak and milestones."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_streak',
    )
    current_streak = models.IntegerField(default=0, help_text='Current consecutive days')
    longest_streak = models.IntegerField(default=0, help_text='All-time best streak')
    last_entry_date = models.DateField(null=True, blank=True)
    total_entries = models.IntegerField(default=0)
    # Grace tokens — using one bridges a single missed day so the streak
    # survives. Topped up by a Celery beat at the start of each calendar
    # month (capped at FREEZE_TOKEN_CAP). Refunded if the user back-fills
    # the missed day via NoteDetailPage edit. See services/streaks.py.
    freeze_tokens = models.IntegerField(default=1, help_text='Streak-freeze tokens available')
    freeze_tokens_refilled_at = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    FREEZE_TOKEN_CAP = 2  # max accumulation across months

    def __str__(self):
        return f'{self.user.username} — {self.current_streak} days (best: {self.longest_streak})'


class Habit(models.Model):
    """User-defined habit tracking."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#8b5cf6')
    icon = models.CharField(max_length=50, blank=True)

    # Target settings
    target_frequency = models.CharField(max_length=20, default='daily')
    target_count = models.IntegerField(default=1)

    # Reminder — fired by send_due_habit_reminders Celery task every 15 min.
    # reminder_time stored as a wall-clock TimeField; the task interprets it
    # in the habit owner's timezone (CustomUser.timezone). null=opted out.
    reminder_enabled = models.BooleanField(default=False)
    reminder_time = models.TimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active'], name='habit_user_active'),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.name}'


class HabitLog(models.Model):
    """Habit check-in record."""
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-completed_at']
        unique_together = [['habit', 'date']]
        indexes = [
            models.Index(fields=['user', 'date'], name='habitlog_user_date'),
            models.Index(fields=['habit', '-date'], name='habitlog_habit_date'),
        ]

    def __str__(self):
        return f'{self.habit.name} - {self.date}'


class DashboardLayout(models.Model):
    """User's personalized dashboard layout configuration."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_layout',
    )
    layout_config = models.JSONField(
        default=dict,
        help_text='Widget positions and settings: {"widgets": [{"id": "...", "x": 0, "y": 0, "w": 4, "h": 2, "enabled": true}]}',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='dashboard_user'),
        ]

    def __str__(self):
        return f'{self.user.username} - Dashboard Layout'


class UserMetric(models.Model):
    """User-defined custom metric tracking with targets."""
    METRIC_TYPE_CHOICES = [
        ('daily_entries', 'Daily Entries'),
        ('avg_mood', 'Average Mood'),
        ('streak_days', 'Streak Days'),
        ('habit_completion', 'Habit Completion'),
        ('sleep_hours', 'Sleep Hours'),
        ('exercise_minutes', 'Exercise Minutes'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_metrics',
    )
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPE_CHOICES)
    target_value = models.FloatField()
    current_value = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active'], name='usermetric_user_active'),
        ]
        unique_together = [['user', 'metric_type']]

    def __str__(self):
        return f'{self.user.username} - {self.metric_type}: {self.current_value}/{self.target_value}'


class Friendship(models.Model):
    """好友關係（雙向確認後建立）"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships',
    )
    friend = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friends_with',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'friend']]
        indexes = [
            models.Index(fields=['user'], name='friendship_user'),
            models.Index(fields=['friend'], name='friendship_friend'),
        ]

    def __str__(self):
        return f'{self.user.username} ↔ {self.friend.username}'


class FriendRequest(models.Model):
    """好友請求"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_requests',
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['from_user', 'to_user']]
        indexes = [
            models.Index(fields=['to_user', 'status'], name='friendreq_to_status'),
            models.Index(fields=['from_user', 'status'], name='friendreq_from_status'),
        ]

    def __str__(self):
        return f'{self.from_user.username} → {self.to_user.username} ({self.status})'


class SharedWithFriend(models.Model):
    """與好友分享日記的記錄"""
    note = models.ForeignKey(
        MoodNote,
        on_delete=models.CASCADE,
        related_name='friend_shares',
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes_shared_with_friends',
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes_received_from_friends',
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-shared_at']
        unique_together = [['note', 'shared_with']]
        indexes = [
            models.Index(fields=['shared_with', '-shared_at'], name='friendshare_with_date'),
            models.Index(fields=['shared_by', '-shared_at'], name='friendshare_by_date'),
        ]

    def __str__(self):
        return f'{self.shared_by.username} shared note with {self.shared_with.username}'


class FriendComment(models.Model):
    """好友對分享日記的留言"""
    share = models.ForeignKey(
        SharedWithFriend,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    commenter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    # Friend comments on shared notes — Fernet-encrypted (same threat model
    # as Message/DM content).
    content = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['share', 'created_at'], name='friendcomment_share_date'),
        ]

    def __str__(self):
        return f'Comment by {self.commenter.username} on share #{self.share.id}'


class PublicPost(models.Model):
    """匿名發布到社群的日記貼文（不加密，公開可見）"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='public_posts',
    )
    content = models.TextField(help_text='Post content (not encrypted)')
    sentiment_score = models.FloatField(null=True, blank=True, help_text='AI-analyzed sentiment score')
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text='Auto-detected category: anxiety, stress, happiness, etc.',
    )
    is_active = models.BooleanField(default=True, help_text='User can deactivate their own posts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='publicpost_created'),
            models.Index(fields=['user', '-created_at'], name='publicpost_user_created'),
            models.Index(fields=['category', '-created_at'], name='publicpost_category_created'),
            models.Index(fields=['is_active', '-created_at'], name='publicpost_active_created'),
        ]

    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f'Post by {self.user.username}: {preview}'


class PostReaction(models.Model):
    """對公開貼文的反應（擁抱、支持、愛心等）"""
    REACTION_CHOICES = [
        ('hug', 'Hug'),
        ('support', 'Support'),
        ('heart', 'Heart'),
    ]

    post = models.ForeignKey(
        PublicPost,
        on_delete=models.CASCADE,
        related_name='reactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_reactions',
    )
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['post', 'user', 'reaction_type']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'reaction_type'], name='reaction_post_type'),
            models.Index(fields=['user', '-created_at'], name='reaction_user_created'),
        ]

    def __str__(self):
        return f'{self.user.username} {self.reaction_type} on post #{self.post.id}'


class PostReport(models.Model):
    """User-submitted report on a PublicPost. Multiple reports can stack on
    the same post; admins resolve them via ModeratePostView. A post is
    auto-hidden once REPORT_AUTOHIDE_THRESHOLD (default 3) distinct users
    report it — crude but effective abuse defense before manual review."""

    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment / Bullying'),
        ('hate', 'Hate speech'),
        ('self_harm', 'Self-harm / Suicide'),
        ('sexual', 'Sexual content'),
        ('violence', 'Violence / Threats'),
        ('misinfo', 'Misinformation'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('reviewed_kept', 'Reviewed — post kept'),
        ('reviewed_removed', 'Reviewed — post removed'),
        ('dismissed', 'Dismissed (invalid report)'),
    ]

    post = models.ForeignKey(
        'PublicPost', on_delete=models.CASCADE, related_name='reports',
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='post_reports_filed',
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    # Reporter-supplied free-form note may quote the offending content;
    # Fernet-encrypt at rest.
    note = EncryptedTextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='post_reports_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # One reporter can only report a given post once.
        unique_together = [['post', 'reporter']]
        indexes = [
            models.Index(fields=['status', '-created_at'], name='postreport_status_created'),
            models.Index(fields=['post', '-created_at'], name='postreport_post_created'),
        ]

    def __str__(self):
        return f'Report on post #{self.post_id} by {self.reporter.username} ({self.reason})'


class ImportJob(models.Model):
    """Tracks an asynchronous CSV/JSON import. Created by ImportStartView, run
    by import_notes_task, polled by ImportJobStatusView."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='import_jobs',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    fmt = models.CharField(max_length=10, blank=True, default='')   # 'csv' / 'json'
    filename = models.CharField(max_length=255, blank=True, default='')
    storage_key = models.CharField(max_length=500, blank=True, default='')  # path under MEDIA_ROOT
    mapping = models.JSONField(default=dict, blank=True)
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='importjob_user_created'),
            models.Index(fields=['status', '-created_at'], name='importjob_status_created'),
        ]

    def __str__(self):
        return f'ImportJob #{self.pk} ({self.user.username}, {self.status})'

    @property
    def progress_percent(self):
        if self.total_rows <= 0:
            return 0
        return round(self.processed_rows / self.total_rows * 100, 1)
