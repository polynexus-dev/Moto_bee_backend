from django.urls import path
from .views import VehicleListCreateView, VehicleUpdateDeleteView


urlpatterns = [

    path("vehicles/", VehicleListCreateView.as_view()),

    path("vehicles/<uuid:pk>/", VehicleUpdateDeleteView.as_view()),
]