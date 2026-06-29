"""HeartBox API view package.

This module hosts the small set of helpers and constants used across multiple
view submodules (auth, notes, analytics, health, counselor, messaging,
wellness, admin, dashboard, ai_chat). Each submodule lives next to this file
and is re-exported at the bottom so ``from api.views import X`` keeps working
for ``api/urls.py``, ``api/tasks.py``, and any external consumers.
"""

import logging

from django.contrib.auth import get_user_model

from rest_framework import generics, permissions
from rest_framework.response import Response


User = get_user_model()
logger = logging.getLogger(__name__)


class IsOwner(permissions.BasePermission):
    """Object-level permission: caller must own the object.

    Defense in depth: every view already filters its queryset by
    ``user=request.user``, but if a future refactor weakens that filter
    (or a fan-out via ``select_related``/``prefetch_related`` exposes a
    cross-user row), this object-level check still refuses on
    ``has_object_permission``. Attach as a second permission class on
    Retrieve/Update/Destroy views.
    """
    message = 'You do not have permission to access this object.'

    def has_object_permission(self, request, view, obj):
        owner_id = getattr(obj, 'user_id', None)
        if owner_id is None:
            # Fallback for objects whose owner is on a different attr name
            # (e.g. SharedNote.shared_with). Caller views with non-standard
            # ownership shape should set ``owner_attr`` on the view.
            attr = getattr(view, 'owner_attr', 'user')
            owner = getattr(obj, attr, None)
            owner_id = getattr(owner, 'id', None) if owner is not None else None
        return owner_id == getattr(request.user, 'id', None)


def error_response(code, fallback, status_code=400):
    """Return a DRF Response with both a human-readable detail and a machine-readable code.

    Frontend can use ``response.data.code`` to look up an i18n key (``error.<code>``).
    The ``detail`` field is kept for backward compatibility.
    """
    return Response({'detail': fallback, 'code': code}, status=status_code)


# ===== Constants =====
MAX_BATCH_DELETE = 50
MAX_MESSAGE_LENGTH = 5000
MAX_AI_CHAT_MESSAGE_LENGTH = 2000
MAX_EXPORT_NOTES = 5000
CACHE_TTL_ANALYTICS = 300       # 5 minutes
CACHE_TTL_CALENDAR = 300        # 5 minutes
CACHE_TTL_YEAR_PIXELS = 3600    # 1 hour
CACHE_TTL_DAILY_PROMPT = 86400  # 24 hours

def _get_llm_provider_or_none():
    """Return the configured LLM provider, or None if it can't serve a request.

    Callers (daily prompt, weekly summary) should skip the AI call entirely
    when this returns None — falling back to the template path is preferable
    to surfacing a generic error to the user. The provider's
    ``is_configured()`` returns False when ``LLM_SERVER_URL`` or
    ``LLM_SERVER_API_KEY`` is empty, so a missing config does NOT block
    on a 10-second connect timeout.
    """
    from api.services.llm import get_llm_provider
    provider = get_llm_provider()
    return provider if provider.is_configured() else None


def create_notification_if_enabled(user, notification_type, **kwargs):
    """Create a Notification only if the user hasn't disabled this type."""
    from ..models import Notification, NotificationPreference
    pref = NotificationPreference.objects.filter(
        user=user, notification_type=notification_type,
    ).first()
    if pref and not pref.enabled:
        return None
    return Notification.objects.create(user=user, type=notification_type, **kwargs)


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


# ============================================================================
# Feedback (the only user-facing view that stays in this module — other views
# moved to topic submodules below)
# ============================================================================
from ..serializers import FeedbackSerializer  # noqa: E402


class FeedbackCreateView(generics.CreateAPIView):
    serializer_class = FeedbackSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ============================================================================
# Sub-module re-exports (so `from api.views import X` keeps working).
# Order matters: helpers/constants/User/logger above MUST be defined before
# these imports, because each submodule imports from `.` (this module).
# ============================================================================
from .ai_chat import (  # noqa: E402
    AIChatSendMessageView,
    AIChatSessionDetailView,
    AIChatSessionListCreateView,
)
from .auth import (  # noqa: E402
    CancelAccountDeletionView,
    DeleteAccountView,
    ForgotPasswordView,
    GoogleLoginCallbackView,
    IsEmailVerified,
    Login2FAView,
    LoginView,
    LogoutOtherDevicesView,
    LogoutView,
    ProfileView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    SubmitConsentView,
    GuardianConfirmView,
    TOTPBackupCodesView,
    TOTPDisableView,
    TOTPSetupView,
    TOTPVerifyView,
    VerifyEmailView,
    VersionedTokenObtainPairSerializer,
    VersionedTokenRefreshSerializer,
)
from .notes import (  # noqa: E402
    ExportCSVView,
    ExportDataView,
    ExportPDFView,
    ImportCSVView,
    ImportJobStatusView,
    MoodNoteViewSet,
    NoteAttachmentUploadView,
    NoteSharesListView,
    OnThisDayView,
    PreviewCSVView,
    ShareNoteView,
    SharedNotesReceivedView,
    TagViewSet,
    UnshareNoteView,
)
from .analytics import (  # noqa: E402
    AISuggestionsView,
    AlertsView,
    AnalyticsView,
    MyProgressView,
    CalendarView,
    DailyPromptView,
    PersonalSuggestionView,
    JournalStreakView,
    MonthlyReviewView,
    MoodPredictionView,
    SelfAssessmentListCreateView,
    ShareAssessmentView,
    SharedAssessmentsReceivedView,
    YearPixelsView,
    YearlyReviewView,
)
from .health import (  # noqa: E402
    DailySleepListView,
    DailySleepView,
    ErrorReportView,
    HabitAnalyticsView,
    HabitViewSet,
    HealthMetricListView,
    HealthSummaryView,
    HealthSyncView,
    ReminderSettingsView,
    SleepAnalysisView,
    SleepCalendarView,
    SleepInsightsView,
    SleepTrendsView,
    WeeklySummaryListView,
    WeeklySummaryView,
)
from .counselor import (  # noqa: E402
    AvailableSlotsView,
    BookingActionView,
    BookingCreateView,
    BookingListView,
    BookingPagination,
    BookingUserCancelView,
    CounselorApplyView,
    CounselorListView,
    CounselorMyProfileView,
    CounselorReviewCreateView,
    CounselorReviewListView,
    TherapistReportCreateView,
    TherapistReportListView,
    TherapistReportPublicView,
    TimeSlotListView,
)
from .messaging import (  # noqa: E402
    ConversationCreateView,
    ConversationDeleteView,
    ConversationListView,
    ConversationPagination,
    MessageListView,
    QuoteActionView,
)
from .wellness import (  # noqa: E402
    AchievementCheckView,
    AchievementsView,
    CourseDetailView,
    CourseListView,
    LessonCompleteView,
    PsychoArticleDetailView,
    PsychoArticleListView,
    WellnessSessionListCreateView,
    WellnessSessionPagination,
)
from .admin import (  # noqa: E402
    AdminAuditLogView,
    AdminCounselorActionView,
    AdminMLStatusView,
    AdminCounselorListView,
    AdminFeedbackListView,
    AdminStatsView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserPagination,
    IsAdminUser,
)
from .dashboard import (  # noqa: E402
    DashboardLayoutResetView,
    DashboardLayoutView,
    DashboardWidgetDataView,
    MySubscriptionView,
    NotificationListView,
    NotificationPagination,
    NotificationPreferenceView,
    NotificationReadView,
    PushSubscriptionView,
    RequireTier,
    SubscriptionPlanListView,
    UserMetricDetailView,
    UserMetricListView,
    UserMetricRefreshView,
    send_push_notification,
)


# ============================================================================
# drf_spectacular schema policy
# ----------------------------------------------------------------------------
# These APIViews handle internal flows or have non-trivial response shapes
# (computed dicts, side-effect endpoints, admin-only). Setting schema = None
# tells drf_spectacular to skip them without emitting "unable to guess
# serializer" warnings during OpenAPI generation.
#
# To document one of them: remove it from this list and either set
# `serializer_class = X` on the class or wrap it with @extend_schema(...).
# The properly-documented ViewSets (TagViewSet, MoodNoteViewSet, etc.) already
# expose a working schema; this list only suppresses the un-introspectable
# tail.
# ============================================================================
_UNDOCUMENTED_VIEWS = [
    'AcceptFriendRequestView', 'AchievementCheckView', 'AchievementsView',
    'AddCommentView', 'AdminCounselorActionView', 'AdminStatsView',
    'AIChatSendMessageView', 'AIChatSessionDetailView', 'AIChatSessionListCreateView',
    'AISuggestionsView', 'AlertsView', 'AnalyticsView',
    'AvailableSlotsView', 'BookingActionView', 'BookingCreateView',
    'BookingUserCancelView', 'CalendarView', 'ConversationCreateView',
    'ConversationDeleteView', 'CounselorReviewCreateView', 'DailyPromptView',
    'PersonalSuggestionView',
    'DailySleepView', 'DashboardLayoutResetView', 'DashboardLayoutView',
    'CancelAccountDeletionView', 'DashboardWidgetDataView', 'DeleteAccountView', 'DeleteCommentView',
    'ErrorReportView', 'ExportCSVView', 'ExportDataView', 'ExportPDFView',
    'ForgotPasswordView', 'FriendActivityView', 'FriendRequestCreateView',
    'GoogleLoginCallbackView', 'HabitAnalyticsView', 'HealthSummaryView',
    'HealthSyncView', 'ImportCSVView', 'ImportJobStatusView', 'JournalStreakView',
    'LessonCompleteView', 'Login2FAView', 'LogoutOtherDevicesView',
    'MessageListView', 'MonthlyReviewView', 'MoodPredictionView',
    'MySubscriptionView', 'NoteAttachmentUploadView', 'NotificationPreferenceView',
    'NotificationReadView', 'OnThisDayView', 'PreviewCSVView',
    'PushSubscriptionView', 'QuoteActionView', 'RejectFriendRequestView',
    'ReminderSettingsView', 'RemoveFriendView', 'ResendVerificationView',
    'ResetPasswordView', 'ShareAssessmentView', 'ShareNoteView',
    'ShareNoteWithFriendsView', 'SleepAnalysisView', 'SleepCalendarView',
    'SleepInsightsView', 'SleepTrendsView', 'TherapistReportPublicView',
    'TimeSlotListView', 'TOTPBackupCodesView', 'TOTPDisableView',
    'TOTPSetupView', 'TOTPVerifyView', 'UnshareNoteView', 'UserMetricDetailView',
    'UserMetricListView', 'UserMetricRefreshView', 'UserSearchView',
    'VerifyEmailView', 'WeeklySummaryView', 'YearlyReviewView',
    'YearPixelsView',
]
for _name in _UNDOCUMENTED_VIEWS:
    _cls = globals().get(_name)
    if _cls is not None:
        _cls.schema = None
