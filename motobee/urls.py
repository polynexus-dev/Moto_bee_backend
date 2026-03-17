"""motobee/urls.py"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from garages.views import ServiceOffersView, CuratedServicesView, ServiceSearchView
from utils.views import ReverseGeocodeView, NearbyGaragesView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/garages/', include('garages.urls')),
    path('api/v1/bookings/', include('bookings.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/services/offers/', ServiceOffersView.as_view(), name='service-offers'),
    path('api/v1/services/curated/', CuratedServicesView.as_view(), name='service-curated'),
    path('api/v1/services/search/', ServiceSearchView.as_view(), name='service-search'),
    path('api/v1/utils/reverse-geocode/', ReverseGeocodeView.as_view(), name='reverse-geocode'),
    path('api/v1/utils/nearby-garages/', NearbyGaragesView.as_view(), name='nearby-garages'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
