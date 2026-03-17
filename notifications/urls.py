from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('read-all/', views.MarkAllReadView.as_view(), name='notification-read-all'),
    path('<uuid:pk>/read/', views.MarkReadView.as_view(), name='notification-read'),
]
