from django.urls import path
from . import views

urlpatterns = [
    # Garages
    path('', views.GarageListCreateView.as_view(), name='garage-list'),
    path('mine/', views.MyGarageView.as_view(), name='garage-mine'),
    path('<uuid:pk>/', views.GarageDetailView.as_view(), name='garage-detail'),
    path('<uuid:pk>/services/', views.GarageServicesView.as_view(), name='garage-services'),

    # Schedule
    path('<uuid:garage_id>/schedule/', views.ScheduleListView.as_view(), name='schedule-list'),
    path('<uuid:garage_id>/schedule/<str:date>/', views.ScheduleDateView.as_view(), name='schedule-date'),
]
