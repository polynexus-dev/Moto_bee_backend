# urls.py
from django.urls import path
from .views import UserLocationProfileListView, UserLocationProfileDetailView

urlpatterns = [
    path('location-profile/',        UserLocationProfileListView.as_view(),   name='location-profile-list'),
    path('location-profile/<int:pk>/', UserLocationProfileDetailView.as_view(), name='location-profile-detail'),
]