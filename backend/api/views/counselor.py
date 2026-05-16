"""Counselor profiles, reviews, time slots, bookings, and therapist reports.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

from datetime import datetime, timedelta

import rest_framework.pagination
import rest_framework.throttling
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from rest_framework import exceptions, generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from ..models import (
    Booking, CounselorProfile, CounselorReview, MoodNote, SelfAssessment,
    TherapistReport, TimeSlot,
)
from ..serializers import (
    BookingSerializer, CounselorListSerializer, CounselorProfileSerializer,
    CounselorReviewSerializer, TherapistReportPublicSerializer,
    TherapistReportSerializer, TimeSlotSerializer,
)
from ..throttles import BookingThrottle, GeneralWriteThrottle

from . import (
    User, _push_ws_notification, create_notification_if_enabled,
    error_response,
)


class CounselorApplyView(generics.CreateAPIView):
    """User applies to become a counselor."""
    serializer_class = CounselorProfileSerializer

    def perform_create(self, serializer):
        if CounselorProfile.objects.filter(user=self.request.user).exists():
            raise exceptions.ValidationError({'detail': 'You have already applied as a counselor.'})
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
    """List all approved counselors (public for authenticated users), excluding self.

    Supports ``?recommended=true`` to sort counselors by relevance to the
    current user's most frequently used mood-note tags.
    """
    serializer_class = CounselorListSerializer

    def get_queryset(self):
        qs = CounselorProfile.objects.filter(status='approved').exclude(user=self.request.user).select_related('user').annotate(
            avg_rating=Avg('user__received_reviews__rating'),
            review_count=Count('user__received_reviews'),
        )

        if self.request.query_params.get('recommended') == 'true' and self.request.user.is_authenticated:
            # Get user's frequently used tags
            user_notes = MoodNote.objects.filter(user=self.request.user, is_deleted=False)
            tag_counts = {}
            for metadata in user_notes.values_list('metadata', flat=True)[:100]:
                for tag in (metadata or {}).get('tags', []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:5]

            if top_tags:
                q = Q()
                for tag in top_tags:
                    q |= Q(specialty__icontains=tag)
                # Annotate with a match flag so recommended counselors appear first
                from django.db.models import Case, When, Value, IntegerField
                qs = qs.annotate(
                    is_recommended=Case(
                        When(q, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ).order_by('-is_recommended', '-created_at')

        return qs


class CounselorReviewCreateView(APIView):
    """POST /reviews/ — leave a review for a completed booking."""
    throttle_classes = [GeneralWriteThrottle]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        rating = request.data.get('rating')
        content = request.data.get('content', '')

        if not booking_id or not rating:
            return error_response('missing_fields', 'booking_id and rating are required.', 400)

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            return error_response('invalid_rating', 'Rating must be between 1 and 5.', 400)

        try:
            booking = Booking.objects.get(id=booking_id, user=request.user, status='completed')
        except Booking.DoesNotExist:
            return error_response('booking_not_found', 'Completed booking not found.', 404)

        if CounselorReview.objects.filter(booking=booking).exists():
            return error_response('already_reviewed', 'This booking has already been reviewed.', 400)

        review = CounselorReview.objects.create(
            user=request.user,
            counselor=booking.counselor,
            booking=booking,
            rating=rating,
            content=content,
        )
        return Response(CounselorReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class CounselorReviewListView(generics.ListAPIView):
    """GET /counselors/{id}/reviews/ — list reviews for a counselor."""
    serializer_class = CounselorReviewSerializer

    def get_queryset(self):
        counselor_id = self.kwargs['counselor_id']
        return CounselorReview.objects.filter(
            counselor_id=counselor_id,
        ).select_related('user')


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
    """Get available slots for a counselor on a given date.

    counselor_id in the URL is CounselorProfile.pk, but TimeSlot/Booking
    reference User.pk, so we resolve the profile first.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, counselor_id):
        date_str = request.query_params.get('date')
        if not date_str:
            return error_response('date_required', 'Please provide a date parameter.')

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return error_response('invalid_date_format', 'Invalid date format. Use YYYY-MM-DD.')

        # Resolve CounselorProfile.pk → User.pk
        try:
            profile = CounselorProfile.objects.get(pk=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return error_response('counselor_not_found', 'Counselor not found.', 404)
        user_id = profile.user_id

        day_of_week = target_date.weekday()
        slots = TimeSlot.objects.filter(
            counselor_id=user_id,
            day_of_week=day_of_week,
            is_active=True,
        )

        # Exclude already booked slots
        booked = Booking.objects.filter(
            counselor_id=user_id,
            date=target_date,
            status__in=['pending', 'confirmed'],
        ).values_list('start_time', 'end_time')
        booked_set = set(booked)

        available = []
        for slot in slots:
            if (slot.start_time, slot.end_time) not in booked_set:
                available.append(TimeSlotSerializer(slot).data)

        return Response(available)


class BookingPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 50


class BookingListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    pagination_class = BookingPagination

    def get_queryset(self):
        user = self.request.user
        return Booking.objects.filter(
            Q(user=user) | Q(counselor=user)
        ).select_related('user', 'counselor', 'review').order_by('-created_at')


class BookingCreateView(APIView):
    throttle_classes = [BookingThrottle]

    @transaction.atomic
    def post(self, request):
        counselor_id = request.data.get('counselor_id')
        date_str = request.data.get('date')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        if not all([counselor_id, date_str, start_time, end_time]):
            return error_response('fields_required', 'All required fields must be provided.')

        # Validate time format (HH:MM or HH:MM:SS)
        from datetime import time as dt_time
        try:
            parts = str(start_time).split(':')
            start_t = dt_time(int(parts[0]), int(parts[1]))
            parts = str(end_time).split(':')
            end_t = dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return error_response('invalid_time_format', 'Invalid time format. Use HH:MM.')
        if start_t >= end_t:
            return error_response('start_before_end', 'Start time must be before end time.')

        # Resolve CounselorProfile.pk → User.pk
        try:
            profile = CounselorProfile.objects.get(pk=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return error_response('counselor_not_found', 'Counselor not found.', 404)
        counselor_user_id = profile.user_id

        # Prevent self-booking
        if counselor_user_id == request.user.id:
            return error_response('cannot_book_self', 'You cannot book yourself.')

        # Validate date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return error_response('invalid_date_format', 'Invalid date format. Use YYYY-MM-DD.')
        if target_date < timezone.now().date():
            return error_response('cannot_book_past', 'Cannot book a past date.')

        # Check for conflicts with row-level locking to prevent race condition
        conflict = Booking.objects.select_for_update().filter(
            counselor_id=counselor_user_id,
            date=target_date,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status__in=['pending', 'confirmed'],
        ).exists()
        if conflict:
            return error_response('slot_already_booked', 'This time slot is already booked.', 409)

        booking = Booking.objects.create(
            user=request.user,
            counselor_id=counselor_user_id,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            price=profile.hourly_rate,
        )

        # Notify counselor
        notif = create_notification_if_enabled(
            User.objects.get(pk=counselor_user_id), 'booking',
            title='New booking',
            message=f'{request.user.username} booked {date_str} {start_time}',
            data={
                'booking_id': booking.id,
                'action': 'new',
                'username': request.user.username,
                'date': date_str,
                'time': str(start_time),
            },
        )

        if notif:
            _push_ws_notification(counselor_user_id, notif)

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingActionView(APIView):
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, counselor=request.user)
        except Booking.DoesNotExist:
            return error_response('booking_not_found', 'Booking not found.', 404)

        action_type = request.data.get('action')
        if action_type == 'confirm':
            booking.status = 'confirmed'
        elif action_type == 'cancel':
            booking.status = 'cancelled'
        elif action_type == 'complete':
            booking.status = 'completed'
        else:
            return error_response('booking_action_invalid', 'Action must be "confirm", "cancel", or "complete".')
        booking.save(update_fields=['status'])

        # Notify user
        notif = create_notification_if_enabled(
            booking.user, 'booking',
            title=f'Booking {booking.status}',
            message=f'Your booking with {booking.counselor.username} is now {booking.status}.',
            data={
                'booking_id': booking.id,
                'action': booking.status,
                'counselor_name': booking.counselor.username,
            },
        )

        if notif:
            _push_ws_notification(booking.user_id, notif)

        return Response(BookingSerializer(booking).data)


class BookingUserCancelView(APIView):
    """Allow a user to cancel their own pending or confirmed booking."""

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return error_response('booking_not_found', 'Booking not found.', 404)

        if booking.status not in ('pending', 'confirmed'):
            return error_response('only_pending_confirmed_cancel', 'Only pending or confirmed bookings can be cancelled.')

        booking.status = 'cancelled'
        booking.save(update_fields=['status'])

        # Notify counselor
        notif = create_notification_if_enabled(
            booking.counselor, 'booking',
            title='Booking cancelled',
            message=f'{request.user.username} cancelled their booking.',
            data={
                'booking_id': booking.id,
                'action': 'user_cancelled',
                'username': request.user.username,
            },
        )
        if notif:
            _push_ws_notification(booking.counselor_id, notif)

        return Response(BookingSerializer(booking).data)


class TherapistReportCreateView(generics.CreateAPIView):
    serializer_class = TherapistReportSerializer

    def perform_create(self, serializer):
        user = self.request.user
        period_start = serializer.validated_data['period_start']
        period_end = serializer.validated_data['period_end']
        if period_end < period_start:
            raise exceptions.ValidationError({'detail': 'period_end must be >= period_start.'})

        notes = MoodNote.objects.filter(
            user=user, is_deleted=False,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
            sentiment_score__isnull=False,
        )

        # Build report data snapshot
        mood_data = list(notes.values('created_at', 'sentiment_score', 'stress_index'))
        for item in mood_data:
            item['created_at'] = item['created_at'].isoformat()

        agg = notes.aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

        # Recent assessments
        assessments = list(
            SelfAssessment.objects.filter(
                user=user,
                created_at__date__gte=period_start,
                created_at__date__lte=period_end,
            ).values('assessment_type', 'total_score', 'created_at')
        )
        for a in assessments:
            a['created_at'] = a['created_at'].isoformat()

        report_data = {
            'mood_trends': mood_data,
            'mood_avg': round(agg['avg_s'], 2) if agg['avg_s'] is not None else None,
            'stress_avg': round(agg['avg_st'], 1) if agg['avg_st'] is not None else None,
            'note_count': notes.count(),
            'assessments': assessments,
        }

        serializer.save(
            user=user,
            report_data=report_data,
            expires_at=timezone.now() + timedelta(days=30),
        )


class TherapistReportListView(generics.ListAPIView):
    serializer_class = TherapistReportSerializer

    def get_queryset(self):
        return TherapistReport.objects.filter(user=self.request.user)


class TherapistReportPublicView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [rest_framework.throttling.AnonRateThrottle]

    def get(self, request, token):
        try:
            report = TherapistReport.objects.get(token=token)
        except TherapistReport.DoesNotExist:
            return error_response('report_not_found', 'Report not found.', 404)
        if timezone.now() > report.expires_at:
            return error_response('report_expired', 'This report has expired.', 410)
        return Response(TherapistReportPublicSerializer(report).data)
