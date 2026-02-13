from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AIChatMessage, AIChatSession,
    Booking, Conversation, CounselorProfile, Feedback, Message, MoodNote,
    NoteAttachment, Notification, SharedNote, TimeSlot,
)

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
        fields = ('id', 'username', 'email', 'bio', 'avatar', 'is_counselor', 'is_staff', 'created_at', 'updated_at')
        read_only_fields = ('id', 'username', 'is_staff', 'created_at', 'updated_at')

    def get_is_counselor(self, obj):
        return hasattr(obj, 'counselor_profile') and obj.counselor_profile.is_approved


class MoodNoteSerializer(serializers.ModelSerializer):
    """Full serializer — write accepts plaintext `content`, read returns decrypted."""
    content = serializers.CharField(write_only=True)
    decrypted_content = serializers.CharField(source='content', read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = MoodNote
        fields = (
            'id', 'content', 'decrypted_content',
            'sentiment_score', 'stress_index', 'ai_feedback',
            'is_pinned', 'metadata', 'attachments', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'sentiment_score', 'stress_index', 'ai_feedback', 'created_at', 'updated_at')

    def get_attachments(self, obj):
        return NoteAttachmentSerializer(obj.attachments.all(), many=True).data

    def create(self, validated_data):
        plaintext = validated_data.pop('content')
        note = MoodNote(**validated_data)
        note.set_content(plaintext)
        note.save()
        return note

    def update(self, instance, validated_data):
        plaintext = validated_data.pop('content', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if plaintext is not None:
            instance.set_content(plaintext)
        instance.save()
        return instance


class MoodNoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — only decrypts first 100 chars."""
    content_preview = serializers.CharField(read_only=True)

    class Meta:
        model = MoodNote
        fields = (
            'id', 'content_preview',
            'sentiment_score', 'stress_index',
            'is_pinned', 'metadata', 'created_at',
        )


# ===== Counselor =====

class CounselorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CounselorProfile
        fields = ('id', 'username', 'license_number', 'specialty', 'introduction', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')


class CounselorListSerializer(serializers.ModelSerializer):
    """Public listing of approved counselors."""
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = CounselorProfile
        fields = ('id', 'username', 'avatar', 'specialty', 'introduction')


# ===== Messaging =====

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'sender_name', 'sender_avatar', 'content', 'is_read', 'created_at')
        read_only_fields = ('id', 'sender', 'sender_name', 'is_read', 'created_at')


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

    def get_is_counselor(self, obj):
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

    def get_other_user(self, obj):
        request_user = self.context['request'].user
        other = obj.counselor if obj.user == request_user else obj.user
        avatar = None
        if getattr(other, 'avatar', None):
            request = self.context.get('request')
            avatar = request.build_absolute_uri(other.avatar.url) if request else other.avatar.url
        return {'id': other.id, 'username': other.username, 'avatar': avatar}

    def get_last_message(self, obj):
        # Use prefetched messages to avoid N+1
        msgs = obj.messages.all()
        if msgs:
            msg = max(msgs, key=lambda m: m.created_at)
            return {'content': msg.content[:80], 'created_at': msg.created_at, 'sender_name': msg.sender.username}
        return None

    def get_unread_count(self, obj):
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

    class Meta:
        model = Booking
        fields = ('id', 'user', 'user_name', 'counselor', 'counselor_name',
                  'date', 'start_time', 'end_time', 'status', 'created_at')
        read_only_fields = ('id', 'user', 'counselor', 'status', 'created_at')


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
    author = serializers.SerializerMethodField()
    sentiment_score = serializers.FloatField(source='note.sentiment_score', read_only=True)
    stress_index = serializers.IntegerField(source='note.stress_index', read_only=True)
    note_created_at = serializers.DateTimeField(source='note.created_at', read_only=True)

    class Meta:
        model = SharedNote
        fields = ('id', 'note', 'author', 'note_preview', 'sentiment_score',
                  'stress_index', 'is_anonymous', 'shared_at', 'note_created_at')
        read_only_fields = fields

    def get_author(self, obj):
        if obj.is_anonymous:
            return None
        return obj.note.user.username


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
        fields = ('id', 'title', 'is_active', 'message_count', 'last_message_preview', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message_preview(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return last_msg.content[:80]
        return None
