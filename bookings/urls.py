from django.urls import path
from . import views

urlpatterns = [
    path('', views.BookingCreateView.as_view(), name='booking-create'),
    path('mine/', views.CustomerBookingsView.as_view(), name='booking-mine'),
    path('garage/', views.GarageBookingsView.as_view(), name='booking-garage'),
    path('booked-slots/',views.BookedSlotsView.as_view()), # ← add
    path('<uuid:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('<uuid:pk>/accept/', views.AcceptBookingView.as_view(), name='booking-accept'),
    path('<uuid:pk>/reject/', views.RejectBookingView.as_view(), name='booking-reject'),
    path('<uuid:pk>/start/', views.StartBookingView.as_view(), name='booking-start'),
    path('<uuid:pk>/duration/', views.SetDurationView.as_view(), name='booking-duration'),
    path('<uuid:pk>/complete/', views.CompleteBookingView.as_view(), name='booking-complete'),
    path('<uuid:pk>/cancel/', views.CancelBookingView.as_view(), name='booking-cancel'),
]
