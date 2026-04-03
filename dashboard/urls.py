from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    # read
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/export/', views.api_export_csv, name='api_export'),
    # control (admin only)
    path('api/ue/<int:ue_id>/pathloss/', views.api_pathloss, name='api_pathloss'),
    path('api/ue/<int:ue_id>/toggle/', views.api_toggle_ue, name='api_toggle_ue'),
    path('api/noise/', views.api_noise, name='api_noise'),
]
