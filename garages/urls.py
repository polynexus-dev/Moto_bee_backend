# from django.urls import path
# from . import views

# urlpatterns = [
#     # Garages
#     path('', views.GarageListCreateView.as_view(), name='garage-list'),#get or post
#     path('mine/', views.MyGarageView.as_view(), name='garage-mine'),#get
#     path('<uuid:pk>/', views.GarageDetailView.as_view(), name='garage-detail'),#patch or get
#     path('<uuid:pk>/services/', views.GarageServicesView.as_view(), name='garage-services'),

#     # Schedule
#     path('<uuid:garage_id>/schedule/', views.ScheduleListView.as_view(), name='schedule-list'),
#     path('<uuid:garage_id>/schedule/<str:date>/', views.ScheduleDateView.as_view(), name='schedule-date'),
# ]


from django.urls import path
from . import views

urlpatterns = [
    # ⚠️ Specific routes BEFORE dynamic routes
    path('',               views.GarageListView.as_view(),     name='garage-list'),      # GET, POST
    path('mine/',          views.MyGarageView.as_view(),        name='garage-mine'),      # GET, PATCH
    path('mine/services/', views.GarageServicesView.as_view(),  name='garage-services'),  # PATCH

    # Dynamic routes
    path('<uuid:garage_id>/schedule/', views.GarageScheduleView.as_view(), name='garage-schedule'),  # GET, PATCH
    path('<uuid:id>/',                 views.GarageDetailView.as_view(),   name='garage-detail'),     # GET
]