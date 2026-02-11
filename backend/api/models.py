from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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
    is_pinned = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True, help_text='weather, temperature, location, tags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='moodnote_user_created'),
            models.Index(fields=['user', 'sentiment_score'], name='moodnote_user_sentiment'),
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
        """Decrypted first 100 chars for list views."""
        full = self.content
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
    license_number = models.CharField(max_length=50, help_text='諮商師執照號碼')
    specialty = models.CharField(max_length=200, help_text='專長領域')
    introduction = models.TextField(help_text='自我介紹')
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

    def __str__(self):
        return f'{self.user.username} <-> {self.counselor.username}'


class Message(models.Model):
    """A message in a conversation."""

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['counselor', 'date', 'status'], name='booking_counselor_date'),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.counselor.username} {self.date} {self.start_time}'


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

    def __str__(self):
        return f'Note #{self.note_id} → {self.shared_with.username}'
