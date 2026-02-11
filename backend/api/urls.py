from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    AdminCounselorActionView,
    AdminCounselorListView,
    AdminStatsView,
    AdminUserDetailView,
    AdminUserListView,
    AlertsView,
    AnalyticsView,
    AvailableSlotsView,
    BookingActionView,
    BookingCreateView,
    BookingListView,
    CalendarView,
    ConversationCreateView,
    ConversationListView,
    CounselorApplyView,
    CounselorListView,
    CounselorMyProfileView,
    ExportPDFView,
    MessageListView,
    MoodNoteViewSet,
    NoteAttachmentUploadView,
    NotificationListView,
    NotificationReadView,
    ProfileView,
    RefreshView,
    RegisterView,
    ForgotPasswordView,
    LoginView,
    LogoutOtherDevicesView,
    ResetPasswordView,
    ShareNoteView,
    SharedNotesReceivedView,
    TimeSlotListView,
)

router = DefaultRouter()
router.register(r'notes', MoodNoteViewSet, basename='moodnote')

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/password/forgot/', ForgotPasswordView.as_view(), name='password-forgot'),
    path('auth/password/reset/', ResetPasswordView.as_view(), name='password-reset'),
    path('auth/logout-other-devices/', LogoutOtherDevicesView.as_view(), name='logout-other-devices'),
    # Analytics
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('analytics/calendar/', CalendarView.as_view(), name='analytics-calendar'),
    # Alerts
    path('alerts/', AlertsView.as_view(), name='alerts'),
    # PDF Export (must be before router.urls so it matches before notes/<pk>/)
    path('notes/export/', ExportPDFView.as_view(), name='notes-export'),
    # Counselor
    path('counselors/', CounselorListView.as_view(), name='counselor-list'),
    path('counselors/apply/', CounselorApplyView.as_view(), name='counselor-apply'),
    path('counselors/me/', CounselorMyProfileView.as_view(), name='counselor-me'),
    # Messaging
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/<int:conv_id>/messages/', MessageListView.as_view(), name='message-list'),
    # Admin
    path('admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/counselors/', AdminCounselorListView.as_view(), name='admin-counselors'),
    path('admin/counselors/<int:pk>/action/', AdminCounselorActionView.as_view(), name='admin-counselor-action'),
    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/read/', NotificationReadView.as_view(), name='notification-read'),
    # Attachments
    path('notes/<int:note_id>/attachments/', NoteAttachmentUploadView.as_view(), name='note-attachments'),
    # Schedule
    path('schedule/', TimeSlotListView.as_view(), name='schedule'),
    path('bookings/', BookingListView.as_view(), name='booking-list'),
    path('bookings/create/', BookingCreateView.as_view(), name='booking-create'),
    path('bookings/<int:pk>/action/', BookingActionView.as_view(), name='booking-action'),
    path('counselors/<int:counselor_id>/available/', AvailableSlotsView.as_view(), name='available-slots'),
    # Sharing
    path('notes/<int:note_id>/share/', ShareNoteView.as_view(), name='share-note'),
    path('shared-notes/', SharedNotesReceivedView.as_view(), name='shared-notes'),
    # Notes CRUD
    path('', include(router.urls)),
]
