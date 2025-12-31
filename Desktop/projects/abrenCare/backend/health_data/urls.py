# urls.py
from django.urls import path
from .views import (
    HeartRateViewSet, SleepSessionViewSet, ActivityViewSet,
    DailySummaryViewSet, HealthGoalViewSet, HealthAlertViewSet,
    HealthInsightViewSet, HealthDashboardView, HealthReportView,
    HealthMetricsView, process_health_data, get_health_trends,
    generate_alerts, detect_anomalies
)

urlpatterns = [
    # Heart Rate URLs
    path('heart-rate/', HeartRateViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='heart-rate-list'),
    path('heart-rate/<int:pk>/', HeartRateViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='heart-rate-detail'),
    path('heart-rate/today/', HeartRateViewSet.as_view({'get': 'today'}), name='heart-rate-today'),
    path('heart-rate/range/', HeartRateViewSet.as_view({'get': 'range'}), name='heart-rate-range'),
    path('heart-rate/current/', HeartRateViewSet.as_view({'get': 'current'}), name='heart-rate-current'),
    path('heart-rate/anomalies/', HeartRateViewSet.as_view({'get': 'anomalies'}), name='heart-rate-anomalies'),
    path('heart-rate/stats/', HeartRateViewSet.as_view({'get': 'stats'}), name='heart-rate-stats'),
    path('heart-rate/analyze/', HeartRateViewSet.as_view({'post': 'analyze'}), name='heart-rate-analyze'),
    
    # Sleep Session URLs
    path('sleep/', SleepSessionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='sleep-list'),
    path('sleep/<int:pk>/', SleepSessionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='sleep-detail'),
    path('sleep/recent/', SleepSessionViewSet.as_view({'get': 'recent'}), name='sleep-recent'),
    path('sleep/last-night/', SleepSessionViewSet.as_view({'get': 'last_night'}), name='sleep-last-night'),
    path('sleep/stats/', SleepSessionViewSet.as_view({'get': 'stats'}), name='sleep-stats'),
    path('sleep/<int:pk>/analyze/', SleepSessionViewSet.as_view({'get': 'analyze'}), name='sleep-analyze'),
    path('sleep/patterns/', SleepSessionViewSet.as_view({'get': 'patterns'}), name='sleep-patterns'),
    
    # Activity URLs
    path('activities/', ActivityViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='activities-list'),
    path('activities/<int:pk>/', ActivityViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='activities-detail'),
    path('activities/today/', ActivityViewSet.as_view({'get': 'today'}), name='activities-today'),
    path('activities/recent/', ActivityViewSet.as_view({'get': 'recent'}), name='activities-recent'),
    path('activities/stats/', ActivityViewSet.as_view({'get': 'stats'}), name='activities-stats'),
    path('activities/<int:pk>/analyze/', ActivityViewSet.as_view({'get': 'analyze'}), name='activity-analyze'),
    path('activities/patterns/', ActivityViewSet.as_view({'get': 'patterns'}), name='activities-patterns'),
    path('activities/summary/', ActivityViewSet.as_view({'get': 'summary'}), name='activities-summary'),
    
    # Daily Summary URLs (Read-only)
    path('daily-summary/', DailySummaryViewSet.as_view({'get': 'list'}), name='daily-summary-list'),
    path('daily-summary/<int:pk>/', DailySummaryViewSet.as_view({'get': 'retrieve'}), name='daily-summary-detail'),
    path('daily-summary/today/', DailySummaryViewSet.as_view({'get': 'today'}), name='daily-summary-today'),
    path('daily-summary/recent/', DailySummaryViewSet.as_view({'get': 'recent'}), name='daily-summary-recent'),
    path('daily-summary/stats/', DailySummaryViewSet.as_view({'get': 'stats'}), name='daily-summary-stats'),
    path('daily-summary/trends/', DailySummaryViewSet.as_view({'get': 'trends'}), name='daily-summary-trends'),
    
    # Health Goal URLs
    path('health-goals/', HealthGoalViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='health-goals-list'),
    path('health-goals/<int:pk>/', HealthGoalViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='health-goals-detail'),
    path('health-goals/active/', HealthGoalViewSet.as_view({'get': 'active'}), name='health-goals-active'),
    path('health-goals/completed/', HealthGoalViewSet.as_view({'get': 'completed'}), name='health-goals-completed'),
    path('health-goals/<int:pk>/track/', HealthGoalViewSet.as_view({'post': 'track'}), name='health-goal-track'),
    path('health-goals/<int:pk>/complete/', HealthGoalViewSet.as_view({'post': 'complete'}), name='health-goal-complete'),
    path('health-goals/progress/', HealthGoalViewSet.as_view({'get': 'progress'}), name='health-goals-progress'),
    
    # Health Alert URLs
    path('health-alerts/', HealthAlertViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='health-alerts-list'),
    path('health-alerts/<int:pk>/', HealthAlertViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='health-alerts-detail'),
    path('health-alerts/unread/', HealthAlertViewSet.as_view({'get': 'unread'}), name='health-alerts-unread'),
    path('health-alerts/recent/', HealthAlertViewSet.as_view({'get': 'recent'}), name='health-alerts-recent'),
    path('health-alerts/<int:pk>/read/', HealthAlertViewSet.as_view({'post': 'read'}), name='health-alert-read'),
    path('health-alerts/<int:pk>/acknowledge/', HealthAlertViewSet.as_view({'post': 'acknowledge'}), name='health-alert-acknowledge'),
    path('health-alerts/mark-all-read/', HealthAlertViewSet.as_view({'post': 'mark_all_read'}), name='health-alerts-mark-all-read'),
    path('health-alerts/stats/', HealthAlertViewSet.as_view({'get': 'stats'}), name='health-alerts-stats'),
    
    # Health Insight URLs
    path('health-insights/', HealthInsightViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='health-insights-list'),
    path('health-insights/<int:pk>/', HealthInsightViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='health-insights-detail'),
    path('health-insights/new/', HealthInsightViewSet.as_view({'get': 'new'}), name='health-insights-new'),
    path('health-insights/recent/', HealthInsightViewSet.as_view({'get': 'recent'}), name='health-insights-recent'),
    path('health-insights/<int:pk>/read/', HealthInsightViewSet.as_view({'post': 'read'}), name='health-insight-read'),
    path('health-insights/<int:pk>/apply/', HealthInsightViewSet.as_view({'post': 'apply'}), name='health-insight-apply'),
    path('health-insights/<int:pk>/dismiss/', HealthInsightViewSet.as_view({'post': 'dismiss'}), name='health-insight-dismiss'),
    path('health-insights/mark-all-read/', HealthInsightViewSet.as_view({'post': 'mark_all_read'}), name='health-insights-mark-all-read'),
    path('health-insights/stats/', HealthInsightViewSet.as_view({'get': 'stats'}), name='health-insights-stats'),
    path('health-insights/generate/', HealthInsightViewSet.as_view({'get': 'generate'}), name='health-insights-generate'),
    
    # Dashboard & Report URLs
    path('dashboard/', HealthDashboardView.as_view(), name='health-dashboard'),
    path('report/', HealthReportView.as_view(), name='health-report'),
    path('metrics/', HealthMetricsView.as_view(), name='metrics'),
    
    # Processing URLs
    path('process-health-data/', process_health_data, name='process-health-data'),
    path('health-trends/', get_health_trends, name='get-health-trends'),
    path('generate-alerts/', generate_alerts, name='generate-alerts'),
    path('detect-anomalies/', detect_anomalies, name='detect-anomalies'),
]
