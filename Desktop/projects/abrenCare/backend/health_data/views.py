from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg, Max, Min
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
import logging

from .models import (
    HeartRateReading, SleepSession, Activity, DailySummary,
    HealthGoal, HealthAlert, HealthInsight
)
from .serializers import (
    HeartRateReadingSerializer, SleepSessionSerializer, ActivitySerializer,
    DailySummarySerializer, HealthGoalSerializer, HealthAlertSerializer,
    HealthInsightSerializer, HealthMetricsSerializer, HealthTrendsSerializer,
    HealthRecommendationSerializer
)
from .services import HealthDataService
from .health_analyzer import HealthAnalyzer
from .anomaly_detector import AnomalyDetector
from .heart_rate_processor import HeartRateProcessor
from .sleep_processor import SleepProcessor
from .activity_processor import ActivityProcessor

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class HeartRateViewSet(viewsets.ModelViewSet):
    """ViewSet for heart rate readings"""
    serializer_class = HeartRateReadingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['context', 'is_anomaly']
    ordering_fields = ['timestamp', 'bpm', 'created_at']
    ordering = ['-timestamp']
    search_fields = ['context', 'anomaly_type']
    
    def get_queryset(self):
        return HeartRateReading.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's heart rate readings"""
        today = timezone.now().date()
        readings = self.get_queryset().filter(timestamp__date=today)
        
        page = self.paginate_queryset(readings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(readings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def range(self, request):
        """Get heart rate readings within a date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if not start_date:
            return Response(
                {'error': 'start_date parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            timestamp__date__range=[start_date, end_date]
        )
        
        # Return aggregated data for charts
        data = queryset.extra({'date': "date(timestamp)"}).values('date').annotate(
            avg_bpm=Avg('bpm'),
            min_bpm=Min('bpm'),
            max_bpm=Max('bpm'),
            count=Count('id')
        ).order_by('date')
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current heart rate (most recent reading)"""
        latest_reading = self.get_queryset().order_by('-timestamp').first()
        
        if not latest_reading:
            return Response(
                {'detail': 'No heart rate data available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(latest_reading)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def anomalies(self, request):
        """Get heart rate anomalies"""
        anomalies = self.get_queryset().filter(is_anomaly=True)
        
        page = self.paginate_queryset(anomalies)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(anomalies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get heart rate statistics"""
        queryset = self.get_queryset()
        
        # Date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if start_date:
            queryset = queryset.filter(timestamp__date__range=[start_date, end_date])
        
        # Context filter
        context = request.query_params.get('context')
        if context:
            queryset = queryset.filter(context=context)
        
        stats = queryset.aggregate(
            avg_bpm=Avg('bpm'),
            min_bpm=Min('bpm'),
            max_bpm=Max('bpm'),
            total_readings=Count('id'),
            anomaly_count=Count('id', filter=Q(is_anomaly=True))
        )
        
        # Calculate resting heart rate (lowest average from rest/sleep context)
        resting_readings = queryset.filter(context__in=['rest', 'sleep'])
        resting_hr = resting_readings.aggregate(avg=Avg('bpm'))['avg'] if resting_readings.exists() else None
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'statistics': stats,
            'resting_heart_rate': resting_hr,
            'anomaly_percentage': (
                (stats['anomaly_count'] / stats['total_readings'] * 100) 
                if stats['total_readings'] > 0 else 0
            )
        })
    
    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """Analyze heart rate data for anomalies and patterns"""
        try:
            days = int(request.data.get('days', 7))
            
            analyzer = AnomalyDetector(self.request.user)
            anomalies = analyzer.detect_heart_rate_anomalies(
                start_time=timezone.now() - timedelta(days=days)
            )
            
            return Response({
                'success': True,
                'days_analyzed': days,
                'anomalies_found': len(anomalies),
                'anomalies': anomalies[:10]  # Return first 10 for performance
            })
            
        except Exception as e:
            logger.error(f"Heart rate analysis failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SleepSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for sleep sessions"""
    serializer_class = SleepSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['quality_category']
    ordering_fields = ['start_time', 'end_time', 'quality_score', 'duration_minutes']
    ordering = ['-start_time']
    search_fields = ['notes']
    
    def get_queryset(self):
        return SleepSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent sleep sessions (last 30 days)"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        sessions = self.get_queryset().filter(start_time__gte=thirty_days_ago)
        
        page = self.paginate_queryset(sessions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def last_night(self, request):
        """Get last night's sleep session"""
        yesterday = timezone.now().date() - timedelta(days=1)
        session = self.get_queryset().filter(start_time__date=yesterday).first()
        
        if not session:
            return Response(
                {'detail': 'No sleep data for last night'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get sleep statistics"""
        queryset = self.get_queryset()
        
        # Date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if start_date:
            queryset = queryset.filter(start_time__date__range=[start_date, end_date])
        
        stats = queryset.aggregate(
            avg_duration=Avg('duration_minutes'),
            avg_quality_score=Avg('quality_score'),
            avg_efficiency=Avg('sleep_efficiency'),
            total_sessions=Count('id'),
            restless_nights=Count('id', filter=Q(was_restless=True))
        )
        
        # Calculate sleep debt
        optimal_hours = 7.5
        total_sleep_hours = (stats['avg_duration'] or 0) / 60 * stats['total_sessions']
        optimal_total_hours = optimal_hours * stats['total_sessions']
        sleep_debt = max(0, optimal_total_hours - total_sleep_hours)
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': stats['total_sessions']
            },
            'statistics': stats,
            'sleep_debt_hours': round(sleep_debt, 1),
            'restless_percentage': (
                (stats['restless_nights'] / stats['total_sessions'] * 100) 
                if stats['total_sessions'] > 0 else 0
            )
        })
    
    @action(detail=True, methods=['get'])
    def analyze(self, request, pk=None):
        """Analyze a specific sleep session"""
        sleep_session = self.get_object()
        
        try:
            analyzer = SleepProcessor()
            analysis = analyzer.analyze_sleep_session(sleep_session)
            
            return Response({
                'success': True,
                'sleep_session': self.get_serializer(sleep_session).data,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Sleep analysis failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def patterns(self, request):
        """Analyze sleep patterns over time"""
        try:
            days = int(request.query_params.get('days', 14))
            
            analyzer = SleepProcessor()
            patterns = analyzer.analyze_sleep_patterns(self.request.user, days=days)
            
            return Response({
                'success': True,
                'patterns': patterns
            })
            
        except Exception as e:
            logger.error(f"Sleep pattern analysis failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for activities"""
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['activity_type', 'intensity']
    ordering_fields = ['start_time', 'end_time', 'duration_minutes', 'calories_burned']
    ordering = ['-start_time']
    search_fields = ['activity_type', 'notes']
    
    def get_queryset(self):
        return Activity.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's activities"""
        today = timezone.now().date()
        activities = self.get_queryset().filter(start_time__date=today)
        
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent activities (last 7 days)"""
        seven_days_ago = timezone.now() - timedelta(days=7)
        activities = self.get_queryset().filter(start_time__gte=seven_days_ago)
        
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get activity statistics"""
        queryset = self.get_queryset()
        
        # Date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if start_date:
            queryset = queryset.filter(start_time__date__range=[start_date, end_date])
        
        # Activity type filter
        activity_type = request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        stats = queryset.aggregate(
            total_activities=Count('id'),
            total_duration=Sum('duration_minutes'),
            total_calories=Sum('calories_burned'),
            total_steps=Sum('steps'),
            total_distance=Sum('distance_km'),
            avg_duration=Avg('duration_minutes'),
            avg_calories=Avg('calories_burned')
        )
        
        # Group by activity type
        by_type = queryset.values('activity_type').annotate(
            count=Count('id'),
            total_duration=Sum('duration_minutes'),
            total_calories=Sum('calories_burned')
        ).order_by('-count')
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'statistics': stats,
            'by_activity_type': list(by_type),
            'average_daily_minutes': (
                (stats['total_duration'] or 0) / max(1, (queryset.count() / 7 * 30))
            )  # Estimate daily average
        })
    
    @action(detail=True, methods=['get'])
    def analyze(self, request, pk=None):
        """Analyze a specific activity"""
        activity = self.get_object()
        
        try:
            analyzer = ActivityProcessor()
            analysis = analyzer.analyze_activity(activity)
            
            return Response({
                'success': True,
                'activity': self.get_serializer(activity).data,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Activity analysis failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def patterns(self, request):
        """Analyze activity patterns over time"""
        try:
            days = int(request.query_params.get('days', 30))
            
            analyzer = ActivityProcessor()
            patterns = analyzer.analyze_activity_patterns(self.request.user, days=days)
            
            return Response({
                'success': True,
                'patterns': patterns
            })
            
        except Exception as e:
            logger.error(f"Activity pattern analysis failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get activity summary for today"""
        today = timezone.now().date()
        
        activities = self.get_queryset().filter(start_time__date=today)
        
        total_duration = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
        total_calories = activities.aggregate(total=Sum('calories_burned'))['total'] or 0
        total_steps = activities.aggregate(total=Sum('steps'))['total'] or 0
        
        by_type = activities.values('activity_type').annotate(
            count=Count('id'),
            duration=Sum('duration_minutes')
        ).order_by('-duration')
        
        return Response({
            'date': today,
            'summary': {
                'total_activities': activities.count(),
                'total_duration_minutes': total_duration,
                'total_calories': total_calories,
                'total_steps': total_steps
            },
            'by_activity_type': list(by_type),
            'intensity_distribution': activities.values('intensity').annotate(
                count=Count('id')
            ).order_by('intensity')
        })


class DailySummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for daily summaries (read-only)"""
    serializer_class = DailySummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_complete']
    ordering_fields = ['date', 'overall_score', 'total_steps']
    ordering = ['-date']
    
    def get_queryset(self):
        return DailySummary.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's daily summary"""
        today = timezone.now().date()
        summary = self.get_queryset().filter(date=today).first()
        
        if not summary:
            # Create empty summary for today
            summary = DailySummary.objects.create(
                user=self.request.user,
                date=today,
                is_complete=False
            )
        
        serializer = self.get_serializer(summary)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent daily summaries (last 30 days)"""
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        summaries = self.get_queryset().filter(date__gte=thirty_days_ago)
        
        page = self.paginate_queryset(summaries)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(summaries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get daily summary statistics"""
        queryset = self.get_queryset()
        
        # Date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if start_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        
        stats = queryset.aggregate(
            avg_steps=Avg('total_steps'),
            avg_calories=Avg('total_calories'),
            avg_sleep=Avg('sleep_duration_minutes'),
            avg_score=Avg('overall_score'),
            total_days=Count('id'),
            healthy_days=Count('id', filter=Q(is_healthy_day=True)),
            complete_days=Count('id', filter=Q(is_complete=True))
        )
        
        # Calculate streaks
        summaries = list(queryset.order_by('date'))
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        
        for summary in summaries:
            if summary.is_healthy_day:
                temp_streak += 1
                current_streak = temp_streak if summary.date == timezone.now().date() else current_streak
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': stats['total_days']
            },
            'statistics': stats,
            'streaks': {
                'current_healthy_streak': current_streak,
                'longest_healthy_streak': longest_streak,
                'healthy_day_percentage': (
                    (stats['healthy_days'] / stats['total_days'] * 100) 
                    if stats['total_days'] > 0 else 0
                ),
                'completion_rate': (
                    (stats['complete_days'] / stats['total_days'] * 100) 
                    if stats['total_days'] > 0 else 0
                )
            }
        })
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get health trends over time"""
        try:
            days = int(request.query_params.get('days', 30))
            
            service = HealthDataService(self.request.user)
            trends = service.get_health_trends(days=days)
            
            return Response({
                'success': True,
                'trends': trends
            })
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class HealthGoalViewSet(viewsets.ModelViewSet):
    """ViewSet for health goals"""
    serializer_class = HealthGoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['goal_type', 'frequency', 'is_active', 'is_completed']
    ordering_fields = ['created_at', 'progress_percentage', 'target_value']
    ordering = ['-is_primary', '-created_at']
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        return HealthGoal.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active health goals"""
        active_goals = self.get_queryset().filter(is_active=True)
        
        page = self.paginate_queryset(active_goals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_goals, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed health goals"""
        completed_goals = self.get_queryset().filter(is_completed=True)
        
        page = self.paginate_queryset(completed_goals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(completed_goals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def track(self, request, pk=None):
        """Track progress for a health goal"""
        try:
            date_str = request.data.get('date')
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
            
            service = HealthDataService(self.request.user)
            result = service.track_health_goal(pk, date)
            
            if 'error' in result:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'success': True,
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Goal tracking failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a goal as completed"""
        goal = self.get_object()
        
        if goal.is_completed:
            return Response(
                {'error': 'Goal is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        goal.is_completed = True
        goal.completed_at = timezone.now()
        goal.save()
        
        serializer = self.get_serializer(goal)
        return Response({
            'success': True,
            'message': 'Goal marked as completed',
            'goal': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def progress(self, request):
        """Get overall progress for all goals"""
        goals = self.get_queryset().filter(is_active=True)
        
        total_goals = goals.count()
        completed_goals = goals.filter(is_completed=True).count()
        in_progress_goals = goals.filter(is_completed=False).count()
        
        avg_progress = goals.aggregate(avg=Avg('progress_percentage'))['avg'] or 0
        
        # Get goals by type
        by_type = goals.values('goal_type').annotate(
            count=Count('id'),
            avg_progress=Avg('progress_percentage'),
            completed=Count('id', filter=Q(is_completed=True))
        ).order_by('goal_type')
        
        return Response({
            'summary': {
                'total_goals': total_goals,
                'completed_goals': completed_goals,
                'in_progress_goals': in_progress_goals,
                'completion_rate': (completed_goals / total_goals * 100) if total_goals > 0 else 0,
                'average_progress': round(avg_progress, 1)
            },
            'by_type': list(by_type),
            'primary_goal': self.get_serializer(
                goals.filter(is_primary=True).first()
            ).data if goals.filter(is_primary=True).exists() else None
        })


class HealthAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for health alerts"""
    serializer_class = HealthAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['alert_type', 'severity', 'is_read', 'is_acknowledged']
    ordering_fields = ['triggered_at', 'created_at']
    ordering = ['-triggered_at']
    search_fields = ['title', 'message']
    
    def get_queryset(self):
        return HealthAlert.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread alerts"""
        unread_alerts = self.get_queryset().filter(is_read=False)
        
        page = self.paginate_queryset(unread_alerts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(unread_alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent alerts (last 7 days)"""
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_alerts = self.get_queryset().filter(triggered_at__gte=seven_days_ago)
        
        page = self.paginate_queryset(recent_alerts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark alert as read"""
        alert = self.get_object()
        alert.mark_as_read()
        
        serializer = self.get_serializer(alert)
        return Response({
            'success': True,
            'message': 'Alert marked as read',
            'alert': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge alert"""
        alert = self.get_object()
        alert.acknowledge()
        
        serializer = self.get_serializer(alert)
        return Response({
            'success': True,
            'message': 'Alert acknowledged',
            'alert': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all alerts as read"""
        alerts = self.get_queryset().filter(is_read=False)
        updated = alerts.update(is_read=True, read_at=timezone.now())
        
        return Response({
            'success': True,
            'message': f'{updated} alerts marked as read'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get alert statistics"""
        queryset = self.get_queryset()
        
        # Date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if start_date:
            queryset = queryset.filter(triggered_at__date__range=[start_date, end_date])
        
        stats = queryset.aggregate(
            total_alerts=Count('id'),
            unread_alerts=Count('id', filter=Q(is_read=False)),
            acknowledged_alerts=Count('id', filter=Q(is_acknowledged=True)),
            critical_alerts=Count('id', filter=Q(severity='critical')),
            high_alerts=Count('id', filter=Q(severity='high')),
            medium_alerts=Count('id', filter=Q(severity='medium'))
        )
        
        # Group by alert type
        by_type = queryset.values('alert_type').annotate(
            count=Count('id'),
            unread=Count('id', filter=Q(is_read=False))
        ).order_by('-count')
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'statistics': stats,
            'by_alert_type': list(by_type),
            'read_rate': (
                ((stats['total_alerts'] - stats['unread_alerts']) / stats['total_alerts'] * 100) 
                if stats['total_alerts'] > 0 else 0
            )
        })


class HealthInsightViewSet(viewsets.ModelViewSet):
    """ViewSet for health insights"""
    serializer_class = HealthInsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['insight_type', 'category', 'is_new', 'is_applied', 'is_dismissed']
    ordering_fields = ['generated_at', 'confidence', 'created_at']
    ordering = ['-is_new', '-generated_at']
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        return HealthInsight.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def new(self, request):
        """Get new insights"""
        new_insights = self.get_queryset().filter(is_new=True)
        
        page = self.paginate_queryset(new_insights)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(new_insights, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent insights (last 30 days)"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_insights = self.get_queryset().filter(generated_at__gte=thirty_days_ago)
        
        page = self.paginate_queryset(recent_insights)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_insights, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark insight as read"""
        insight = self.get_object()
        insight.mark_as_read()
        
        serializer = self.get_serializer(insight)
        return Response({
            'success': True,
            'message': 'Insight marked as read',
            'insight': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply insight"""
        insight = self.get_object()
        insight.apply_insight()
        
        serializer = self.get_serializer(insight)
        return Response({
            'success': True,
            'message': 'Insight applied',
            'insight': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss insight"""
        insight = self.get_object()
        insight.dismiss()
        
        serializer = self.get_serializer(insight)
        return Response({
            'success': True,
            'message': 'Insight dismissed',
            'insight': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all insights as read"""
        insights = self.get_queryset().filter(is_new=True)
        updated = insights.update(is_new=False)
        
        return Response({
            'success': True,
            'message': f'{updated} insights marked as read'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get insight statistics"""
        queryset = self.get_queryset()
        
        # Date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if start_date:
            queryset = queryset.filter(generated_at__date__range=[start_date, end_date])
        
        stats = queryset.aggregate(
            total_insights=Count('id'),
            new_insights=Count('id', filter=Q(is_new=True)),
            applied_insights=Count('id', filter=Q(is_applied=True)),
            dismissed_insights=Count('id', filter=Q(is_dismissed=True)),
            avg_confidence=Avg('confidence')
        )
        
        # Group by category
        by_category = queryset.values('category').annotate(
            count=Count('id'),
            new=Count('id', filter=Q(is_new=True)),
            applied=Count('id', filter=Q(is_applied=True))
        ).order_by('-count')
        
        # Group by type
        by_type = queryset.values('insight_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'statistics': stats,
            'by_category': list(by_category),
            'by_type': list(by_type),
            'application_rate': (
                (stats['applied_insights'] / stats['total_insights'] * 100) 
                if stats['total_insights'] > 0 else 0
            )
        })
    
    @action(detail=False, methods=['get'])
    def generate(self, request):
        """Generate new insights"""
        try:
            service = HealthDataService(self.request.user)
            results = service.process_recent_data(days=1)
            
            new_insights = results.get('insights', [])
            
            return Response({
                'success': True,
                'generated': len(new_insights),
                'insights': new_insights[:10]  # Return first 10 for performance
            })
            
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class HealthDashboardView(APIView):
    """API view for health dashboard"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get dashboard data"""
        from .services import HealthDataService
        
        service = HealthDataService(request.user)
        
        try:
            # Get current health status
            dashboard_data = service.get_current_health_status()
            
            # Import serializers
            from .serializers import (
                DailySummarySerializer, ActivitySerializer, 
                SleepSessionSerializer, HealthGoalSerializer,
                HealthAlertSerializer, HealthInsightSerializer
            )
            
            # Prepare response data with proper serialization
            response_data = {
                'current_status': dashboard_data['current_status'],
                'today_summary': DailySummarySerializer(dashboard_data['today_summary']).data 
                    if dashboard_data['today_summary'] else None,
                'recent_activities': ActivitySerializer(dashboard_data['recent_activities'], many=True).data,
                'last_sleep': SleepSessionSerializer(dashboard_data['last_sleep']).data 
                    if dashboard_data['last_sleep'] else None,
                'active_goals': HealthGoalSerializer(dashboard_data['active_goals'], many=True).data,
                'recent_alerts': {
                    'list': HealthAlertSerializer(dashboard_data['recent_alerts']['list'], many=True).data,
                    'unread': dashboard_data['recent_alerts']['unread'],
                },
                'recent_insights': HealthInsightSerializer(dashboard_data['recent_insights'], many=True).data,
                'trends': dashboard_data['trends'],
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error in dashboard view: {str(e)}")
            return Response(
                {
                    'error': 'Failed to load dashboard data',
                    'detail': str(e),
                    'fallback_data': {
                        'current_status': {},
                        'today_summary': None,
                        'recent_activities': [],
                        'last_sleep': None,
                        'active_goals': [],
                        'recent_alerts': {'list': [], 'unread': 0},
                        'recent_insights': [],
                        'trends': {'heart_rate': [], 'steps': []}
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class HealthReportView(APIView):
    """API view for health reports"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Generate health report for date range"""
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date', timezone.now().date().isoformat())
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if not start_date:
                # Default to 30 days if no start date provided
                start_date = end_date - timedelta(days=30)
            
            service = HealthDataService(request.user)
            report = service.generate_health_report(start_date, end_date)
            
            return Response({
                'success': True,
                'report': report
            })
            
        except ValueError as e:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class HealthMetricsView(APIView):
    """API view for current health metrics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current health metrics"""
        try:
            user = request.user
            today = timezone.now().date()
            
            # Get or create today's summary
            daily_summary, created = DailySummary.objects.get_or_create(
                user=user,
                date=today,
                defaults={
                    'total_steps': 0,
                    'total_calories': 0,
                    'overall_score': 0,
                    'is_complete': False
                }
            )
            
            # Get current heart rate (most recent reading)
            current_hr = HeartRateReading.objects.filter(
                user=user
            ).order_by('-timestamp').first()
            
            # Get today's activities
            today_activities = Activity.objects.filter(
                user=user,
                start_time__date=today
            )
            
            total_active_minutes = today_activities.aggregate(
                total=Sum('duration_minutes')
            )['total'] or 0
            
            total_calories = today_activities.aggregate(
                total=Sum('calories_burned')
            )['total'] or 0
            
            # Get today's sleep or last night's sleep
            today_sleep = SleepSession.objects.filter(
                user=user,
                start_time__date=today
            ).first()
            
            if not today_sleep:
                # Try to get sleep from last night
                yesterday = today - timedelta(days=1)
                today_sleep = SleepSession.objects.filter(
                    user=user,
                    start_time__date=yesterday
                ).order_by('-start_time').first()
            
            # Get heart rate statistics for today
            heart_rate_today = HeartRateReading.objects.filter(
                user=user,
                timestamp__date=today
            )
            
            hr_stats = heart_rate_today.aggregate(
                avg=Avg('bpm'),
                min=Min('bpm'),
                max=Max('bpm')
            )
            
            # Calculate resting heart rate (from rest/sleep context)
            resting_readings = heart_rate_today.filter(
                context__in=['rest', 'sleep']
            )
            resting_hr = resting_readings.aggregate(avg=Avg('bpm'))['avg'] if resting_readings.exists() else None
            
            # Calculate overall score based on various metrics
            steps_score = min(100, (daily_summary.total_steps / 10000 * 100)) if daily_summary.total_steps else 0
            sleep_score = today_sleep.quality_score if today_sleep and today_sleep.quality_score else 0
            activity_score = min(100, (total_active_minutes / 60 * 100))  # 60 min goal
            
            overall_score = (steps_score + sleep_score + activity_score) / 3
            
            metrics = {
                'date': today.isoformat(),
                'steps': {
                    'current': daily_summary.total_steps or 0,
                    'goal': 10000,  # Default goal
                    'percentage': steps_score
                },
                'heart_rate': {
                    'current': current_hr.bpm if current_hr else None,
                    'resting': resting_hr,
                    'average': hr_stats.get('avg'),
                    'min': hr_stats.get('min'),
                    'max': hr_stats.get('max'),
                    'unit': 'bpm'
                },
                'sleep': {
                    'duration_minutes': today_sleep.duration_minutes if today_sleep else None,
                    'score': today_sleep.quality_score if today_sleep else None,
                    'efficiency': today_sleep.sleep_efficiency if today_sleep else None,
                    'start_time': today_sleep.start_time.isoformat() if today_sleep and today_sleep.start_time else None,
                    'end_time': today_sleep.end_time.isoformat() if today_sleep and today_sleep.end_time else None
                },
                'activity': {
                    'active_minutes': total_active_minutes,
                    'calories_burned': total_calories,
                    'goal_minutes': 60,  # 1 hour goal
                    'activities_count': today_activities.count()
                },
                'overall_score': round(overall_score, 1)
            }
            
            return Response(metrics)
            
        except Exception as e:
            import traceback
            logger.error(f"Error in HealthMetricsView: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return fallback response
            return Response({
                'date': timezone.now().date().isoformat(),
                'steps': {
                    'current': 0,
                    'goal': 10000,
                    'percentage': 0
                },
                'heart_rate': {
                    'current': None,
                    'resting': None,
                    'average': None,
                    'unit': 'bpm'
                },
                'sleep': {
                    'duration_minutes': None,
                    'score': None,
                    'efficiency': None
                },
                'activity': {
                    'active_minutes': 0,
                    'calories_burned': 0,
                    'goal_minutes': 60
                },
                'overall_score': 0
            }, status=status.HTTP_200_OK)  # Still return 200 with empty data
        
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_health_data(request):
    """Process recent health data and generate insights"""
    
    try:
        days = int(request.data.get('days', 1))
        
        service = HealthDataService(request.user)
        results = service.process_recent_data(days=days)
        
        return Response({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Health data processing failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_health_trends(request):
    """Get health trends"""
    
    try:
        metric = request.query_params.get('metric')
        days = int(request.query_params.get('days', 30))
        
        service = HealthDataService(request.user)
        trends = service.get_health_trends(metric=metric, days=days)
        
        return Response({
            'success': True,
            'trends': trends
        })
        
    except Exception as e:
        logger.error(f"Trend retrieval failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_alerts(request):
    """Generate health alerts"""
    
    try:
        analyzer = HealthAnalyzer(request.user)
        alerts = analyzer.generate_health_alerts()
        
        return Response({
            'success': True,
            'alerts_generated': len(alerts),
            'alerts': alerts[:10]  # Return first 10 for performance
        })
        
    except Exception as e:
        logger.error(f"Alert generation failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def detect_anomalies(request):
    """Detect anomalies in health data"""
    
    try:
        detector = AnomalyDetector(request.user)
        report = detector.generate_anomaly_report(days=7)
        
        return Response({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    