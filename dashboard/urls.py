from django.urls import path
from . import views, spa

urlpatterns = [
    path('', spa.spa_shell, name='index'),
    path('scenarios/', spa.spa_shell, name='scenarios_page'),
    path('api/whoami/', spa.api_whoami, name='api_whoami'),
    path('api/csrf/', spa.api_csrf, name='api_csrf'),
    # read
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/export/', views.api_export_csv, name='api_export'),
    # GNU Radio status
    path('api/gnr/status/', views.api_gnr_status, name='api_gnr_status'),
    # control (admin only)
    path('api/ue/<int:ue_id>/pathloss/', views.api_pathloss, name='api_pathloss'),
    path('api/ue/<int:ue_id>/toggle/', views.api_toggle_ue, name='api_toggle_ue'),
    path('api/noise/', views.api_noise, name='api_noise'),
    # testbed control (admin only for start/stop, read for any logged-in user)
    path('api/testbed/status/', views.api_testbed_status, name='api_testbed_status'),
    path('api/testbed/start/',  views.api_testbed_start,  name='api_testbed_start'),
    path('api/testbed/stop/',   views.api_testbed_stop,   name='api_testbed_stop'),
    # process manager: per-component control (admin only for start/stop, read for any logged-in user)
    path('api/testbed/components/', views.api_components, name='api_components'),
    path('api/testbed/components/<str:name>/status/', views.api_component_status, name='api_component_status'),
    path('api/testbed/components/<str:name>/start/', views.api_component_start, name='api_component_start'),
    path('api/testbed/components/<str:name>/stop/', views.api_component_stop, name='api_component_stop'),
    path('api/testbed/components/<str:name>/logs/stream/', views.api_component_logs_stream, name='api_component_logs_stream'),
    # AI
    path('ai/', spa.spa_shell, name='ai_page'),
    path('api/ai/insight/', views.api_ai_insight, name='api_ai_insight'),
    path('api/ai/chat/', views.api_ai_chat, name='api_ai_chat'),
    # scenario engine (admin only for run/stop, read for any logged-in user)
    path('api/scenarios/', views.api_scenarios, name='api_scenarios'),
    path('api/scenarios/<slug:slug>/', views.api_scenario_detail, name='api_scenario_detail'),
    path('api/scenarios/<slug:slug>/run/', views.api_scenario_run, name='api_scenario_run'),
    path('api/runs/', views.api_runs, name='api_runs'),
    path('api/runs/<int:run_id>/', views.api_run_detail, name='api_run_detail'),
    path('api/runs/<int:run_id>/stop/', views.api_run_stop, name='api_run_stop'),
    path('api/runs/<int:run_id>/logs/stream/', views.api_run_logs_stream, name='api_run_logs_stream'),
]
