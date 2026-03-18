"""bookings/views.py"""
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Booking
from .serializers import (
    BookingSerializer, BookingCreateSerializer,
    RejectSerializer, DurationSerializer,
)
from garages.models import Garage
from garages.permissions import IsOwner, IsCustomer
from notifications.tasks import send_booking_notification


class BookingCreateView(generics.CreateAPIView):
    """POST /bookings/ — customer creates a booking."""
    permission_classes = [IsAuthenticated, IsCustomer]
    serializer_class = BookingCreateSerializer

    def perform_create(self, serializer):
        booking = serializer.save(customer=self.request.user)
        send_booking_notification(booking, 'new_booking')


class CustomerBookingsView(generics.ListAPIView):
    """GET /bookings/mine/ — customer's own bookings."""
    permission_classes = [IsAuthenticated, IsCustomer]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(
            customer=self.request.user
        ).select_related('garage', 'customer')


class GarageBookingsView(generics.ListAPIView):
    """GET /bookings/garage/ — all bookings for owner's garage."""
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = BookingSerializer

    def get_queryset(self):
        garage = get_object_or_404(Garage, owner=self.request.user)
        qs = Booking.objects.filter(garage=garage).select_related('customer')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class BookingDetailView(generics.RetrieveAPIView):
    """GET /bookings/{id}/"""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    queryset = Booking.objects.all()


# ─────────────────────────────────────────
# ACTION VIEWS — all use extend_schema so Swagger shows them correctly
# ─────────────────────────────────────────

class AcceptBookingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: BookingSerializer},
        tags=['Bookings'],
        summary='Owner accepts a pending booking',
    )
    def patch(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.garage.owner != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        if booking.status != 'pending':
            return Response({'detail': f'Cannot accept a {booking.status} booking.'}, status=400)
        booking.status = 'accepted'
        booking.save()
        send_booking_notification(booking, 'accepted')
        return Response(BookingSerializer(booking).data)


class RejectBookingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RejectSerializer,
        responses={200: BookingSerializer},
        tags=['Bookings'],
        summary='Owner rejects a booking with optional note',
    )
    def patch(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.garage.owner != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        if booking.status not in ('pending', 'accepted'):
            return Response({'detail': f'Cannot reject a {booking.status} booking.'}, status=400)
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # try:
        #     schedule = DaySchedule.objects.get(garage=booking.garage, date=booking.date)
        #     schedule.unmark_slot(booking.time.replace(':', ''))
        # except DaySchedule.DoesNotExist:
        #     pass
        booking.status = 'rejected'
        booking.rejection_note = serializer.validated_data.get('rejection_note', '')
        booking.save()
        send_booking_notification(booking, 'rejected')
        return Response(BookingSerializer(booking).data)


class StartBookingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: BookingSerializer},
        tags=['Bookings'],
        summary='Owner marks service as started',
    )
    def patch(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.garage.owner != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        if booking.status != 'accepted':
            return Response({'detail': 'Booking must be accepted first.'}, status=400)
        booking.status = 'in_progress'
        booking.service_started_at = timezone.now()
        booking.save()
        send_booking_notification(booking, 'in_progress')
        return Response(BookingSerializer(booking).data)


class SetDurationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=DurationSerializer,
        responses={200: BookingSerializer},
        tags=['Bookings'],
        summary='Owner sets estimated service duration in minutes',
    )
    def patch(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.garage.owner != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        serializer = DurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.estimated_duration_min = serializer.validated_data['estimated_duration_min']
        booking.save()
        return Response(BookingSerializer(booking).data)


class CompleteBookingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: BookingSerializer},
        tags=['Bookings'],
        summary='Owner marks service as completed',
    )
    def patch(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.garage.owner != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        if booking.status != 'in_progress':
            return Response({'detail': 'Booking must be in progress first.'}, status=400)
        booking.status = 'completed'
        booking.completed_at = timezone.now()
        booking.save()
        send_booking_notification(booking, 'completed')
        return Response(BookingSerializer(booking).data)


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: BookingSerializer},
        tags=['Bookings'],
        summary='Customer cancels their booking',
    )
    def patch(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.customer != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        if booking.status in ('completed', 'cancelled'):
            return Response({'detail': f'Cannot cancel a {booking.status} booking.'}, status=400)
        # if booking.status in ('pending', 'accepted'):
            # try:
            #     schedule = DaySchedule.objects.get(garage=booking.garage, date=booking.date)
            #     schedule.unmark_slot(booking.time.replace(':', ''))
            # except DaySchedule.DoesNotExist:
            #     pass
        booking.status = 'cancelled'
        booking.save()
        return Response(BookingSerializer(booking).data)