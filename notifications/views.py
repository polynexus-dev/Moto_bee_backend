"""notifications/views.py"""
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'body', 'is_read', 'created_at', 'booking']


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(tags=['Notifications'], summary='Get all notifications for the logged-in user')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description='Notification marked as read')},
        tags=['Notifications'],
        summary='Mark a single notification as read',
    )
    def patch(self, request, pk):
        notif = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if not notif:
            return Response({'detail': 'Not found.'}, status=404)
        notif.is_read = True
        notif.save()
        return Response({'detail': 'Marked as read.'})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description='All notifications marked as read')},
        tags=['Notifications'],
        summary='Mark all notifications as read',
    )
    def patch(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({'detail': f'{count} notifications marked as read.'})