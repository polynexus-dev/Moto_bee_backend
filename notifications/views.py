"""notifications/views.py

In-app notification CRUD  +  FCM push endpoints.

FCM endpoints mirror the Node.js notification server routes:
  Node POST /notifications/send-single    → POST /api/v1/notifications/send-single/
  Node POST /notifications/send-multiple  → POST /api/v1/notifications/send-multiple/
  Node POST /notifications/send-topic     → POST /api/v1/notifications/send-topic/
  Node POST /notifications/save-token     → POST /api/v1/notifications/save-token/
  Node GET  /notifications/tokens         → GET  /api/v1/notifications/tokens/
"""
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, extend_schema_field
import logging

from .models import Notification, FCMToken
from . import fcm as fcm_service

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Serializers
# ────────────────────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'body', 'is_read', 'created_at', 'booking']


class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMToken
        fields = ['id', 'token', 'created_at']


class SendSingleSerializer(serializers.Serializer):
    token = serializers.CharField()
    title = serializers.CharField()
    body  = serializers.CharField()
    data  = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


class SendMultipleSerializer(serializers.Serializer):
    tokens = serializers.ListField(child=serializers.CharField(), min_length=1)
    title  = serializers.CharField()
    body   = serializers.CharField()
    data   = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


class SendTopicSerializer(serializers.Serializer):
    topic = serializers.CharField()
    title = serializers.CharField()
    body  = serializers.CharField()
    data  = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


# ────────────────────────────────────────────────────────────────────────────
# In-app notification views
# ────────────────────────────────────────────────────────────────────────────

class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(tags=['Notifications'], summary='List all notifications for the logged-in user')
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


# ────────────────────────────────────────────────────────────────────────────
# FCM token management  (mirrors Node: save-token / tokens)
# ────────────────────────────────────────────────────────────────────────────

class SaveFCMTokenView(APIView):
    """
    POST /notifications/save-token/
    Body: { "token": "<fcm_token>" }
    Saves the token for the logged-in user. Idempotent — ignores duplicates.
    Mirrors Node: POST /notifications/save-token
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'token': {'type': 'string'}}}},
        responses={200: FCMTokenSerializer},
        tags=['FCM Tokens'],
        summary='Save FCM device token for the logged-in user',
    )
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token is required'}, status=400)

        obj, created = FCMToken.objects.get_or_create(
            token=token,
            defaults={'user': request.user}
        )
        # If token exists but belongs to another user, re-assign (device switch)
        if not created and obj.user != request.user:
            obj.user = request.user
            obj.save()

        return Response({'success': True, 'id': str(obj.id)}, status=200)


class ListFCMTokensView(APIView):
    """
    GET /notifications/tokens/
    Returns all FCM tokens for the logged-in user.
    Mirrors Node: GET /notifications/tokens
    """
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: FCMTokenSerializer(many=True)},
        tags=['FCM Tokens'],
        summary='List all FCM tokens for the logged-in user',
    )
    def get(self, request):
        tokens = FCMToken.objects.filter(user=request.user)
        return Response({'tokens': [t.token for t in tokens]})


# ────────────────────────────────────────────────────────────────────────────
# FCM push endpoints  (mirrors Node notification service)
# ────────────────────────────────────────────────────────────────────────────

class SendSingleView(APIView):
    """
    POST /notifications/send-single/
    Body: { token, title, body, data? }
    Mirrors Node: POST /notifications/send-single
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=SendSingleSerializer,
        responses={200: {'type': 'object', 'properties': {'success': {'type': 'boolean'}, 'message_id': {'type': 'string'}}}},
        tags=['FCM Push'],
        summary='Send FCM push notification to a single device',
    )
    def post(self, request):
        ser = SendSingleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            message_id = fcm_service.send_to_device(d['token'], d['title'], d['body'], d.get('data'))
            return Response({'success': True, 'message_id': message_id})
        except Exception as e:
            logger.error("FCM send-single error: %s", e)
            return Response({'success': False, 'error': str(e)}, status=500)


class SendMultipleView(APIView):
    """
    POST /notifications/send-multiple/
    Body: { tokens: [], title, body, data? }
    Mirrors Node: POST /notifications/send-multiple
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=SendMultipleSerializer,
        responses={200: {'type': 'object', 'properties': {
            'success': {'type': 'boolean'},
            'success_count': {'type': 'integer'},
            'failure_count': {'type': 'integer'},
        }}},
        tags=['FCM Push'],
        summary='Send FCM push notification to multiple devices',
    )
    def post(self, request):
        ser = SendMultipleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            result = fcm_service.send_to_multiple_devices(
                d['tokens'], d['title'], d['body'], d.get('data')
            )
            return Response({'success': True, **result})
        except Exception as e:
            logger.error("FCM send-multiple error: %s", e)
            return Response({'success': False, 'error': str(e)}, status=500)


class SendTopicView(APIView):
    """
    POST /notifications/send-topic/
    Body: { topic, title, body, data? }
    Mirrors Node: POST /notifications/send-topic
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=SendTopicSerializer,
        responses={200: {'type': 'object', 'properties': {'success': {'type': 'boolean'}, 'message_id': {'type': 'string'}}}},
        tags=['FCM Push'],
        summary='Send FCM push notification to a topic (broadcast)',
    )
    def post(self, request):
        ser = SendTopicSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            message_id = fcm_service.send_to_topic(d['topic'], d['title'], d['body'], d.get('data'))
            return Response({'success': True, 'message_id': message_id})
        except Exception as e:
            logger.error("FCM send-topic error: %s", e)
            return Response({'success': False, 'error': str(e)}, status=500)
