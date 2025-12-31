import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg, Max, Min
# Add numpy import
import numpy as np
from .models import (
    HeartRateReading, SleepSession, Activity, DailySummary,
    HealthGoal, HealthAlert, HealthInsight
)
from .health_analyzer import HealthAnalyzer
from .anomaly_detector import AnomalyDetector
from .heart_rate_processor import HeartRateProcessor
from .sleep_processor import SleepProcessor
from .activity_processor import ActivityProcessor

logger = logging.getLogger(__name__)


class HealthDataService:
    """Main service for health data operations"""
    
    def __init__(self, user):
        self.user = user
        self.analyzer = HealthAnalyzer(user)
        self.anomaly_detector = AnomalyDetector(user)
    
    def process_recent_data(self, days: int = 1) -> Dict[str, Any]:
        """Process recent health data and generate insights"""
        
        results = {
            'processed': {
                'heart_rate': 0,
                'sleep': 0,
                'activity': 0
            },
            'insights': [],
            'alerts': [],
            'anomalies': []
        }
        
        try:
            # Process recent heart rate data
            heart_rate_results = self._process_recent_heart_rate(days)
            results['processed']['heart_rate'] = heart_rate_results.get('processed', 0)
            results['anomalies'].extend(heart_rate_results.get('anomalies', []))
            
            # Process recent sleep data
            sleep_results = self._process_recent_sleep(days)
            results['processed']['sleep'] = sleep_results.get('processed', 0)
            
            # Process recent activity data
            activity_results = self._process_recent_activity(days)
            results['processed']['activity'] = activity_results.get('processed', 0)
            
            # Generate daily insights
            today_insights = self.analyzer.generate_daily_insights()
            results['insights'].extend(today_insights)
            
            # Generate health alerts
            alerts = self.analyzer.generate_health_alerts()
            results['alerts'].extend(alerts)
            
            # Update daily summary
            self._update_daily_summary()
            
            logger.info(f"Processed health data for user {self.user.id}: {results['processed']}")
            
        except Exception as e:
            logger.error(f"Error processing health data for user {self.user.id}: {e}")
            results['error'] = str(e)
        
        return results
    
    def _process_recent_heart_rate(self, days: int) -> Dict[str, Any]:
        """Process recent heart rate data"""
        
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        
        # Get unprocessed heart rate readings
        unprocessed_readings = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__range=[start_time, end_time],
            processed_at__isnull=True
        )
        
        processed_count = 0
        anomalies = []
        
        for reading in unprocessed_readings:
            try:
                # Process individual reading
                reading.processed_at = timezone.now()
                
                # Detect if this is an anomaly (simple rule-based)
                if reading.bpm > 120 and reading.context == 'rest':
                    reading.is_anomaly = True
                    reading.anomaly_type = 'high_resting_hr'
                    anomalies.append({
                        'reading_id': str(reading.id),
                        'timestamp': reading.timestamp,
                        'bpm': reading.bpm,
                        'type': 'high_resting_hr'
                    })
                elif reading.bpm < 50 and reading.context not in ['sleep', 'rest']:
                    reading.is_anomaly = True
                    reading.anomaly_type = 'low_hr'
                    anomalies.append({
                        'reading_id': str(reading.id),
                        'timestamp': reading.timestamp,
                        'bpm': reading.bpm,
                        'type': 'low_hr'
                    })
                
                reading.save()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing heart rate reading {reading.id}: {e}")
                continue
        
        # Run ML anomaly detection on recent data
        try:
            ml_anomalies = self.anomaly_detector.detect_heart_rate_anomalies(
                start_time=start_time,
                end_time=end_time
            )
            anomalies.extend(ml_anomalies)
        except Exception as e:
            logger.error(f"Error in ML anomaly detection: {e}")
        
        return {
            'processed': processed_count,
            'anomalies': anomalies,
            'time_range': {
                'start': start_time,
                'end': end_time
            }
        }
    
    def _process_recent_sleep(self, days: int) -> Dict[str, Any]:
        """Process recent sleep data"""
        
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        
        # Get unprocessed sleep sessions
        unprocessed_sessions = SleepSession.objects.filter(
            user=self.user,
            start_time__range=[start_time, end_time],
            processed_at__isnull=True
        )
        
        processed_count = 0
        
        for session in unprocessed_sessions:
            try:
                # Analyze sleep session
                analysis = SleepProcessor.analyze_sleep_session(session)
                
                # Update session with analysis results
                if 'overall_score' in analysis:
                    session.quality_score = analysis['overall_score']
                
                # Mark as restless if awake time is high
                if session.awake_minutes > 60 or session.interruptions > 10:
                    session.was_restless = True
                
                session.processed_at = timezone.now()
                session.save()
                
                processed_count += 1
                
                # Create sleep insight if quality is poor
                if session.quality_score and session.quality_score < 60:
                    HealthInsight.objects.create(
                        user=self.user,
                        insight_type='warning',
                        category='sleep',
                        title='Poor Sleep Quality',
                        description=f'Sleep quality score of {session.quality_score:.0f}/100 on {session.start_time.date()}.',
                        confidence=0.8,
                        start_date=session.start_time.date(),
                        end_date=session.start_time.date(),
                        generated_by='system'
                    )
                
            except Exception as e:
                logger.error(f"Error processing sleep session {session.id}: {e}")
                continue
        
        return {
            'processed': processed_count,
            'time_range': {
                'start': start_time,
                'end': end_time
            }
        }
    
    def _process_recent_activity(self, days: int) -> Dict[str, Any]:
        """Process recent activity data"""
        
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        
        # Get unprocessed activities
        unprocessed_activities = Activity.objects.filter(
            user=self.user,
            start_time__range=[start_time, end_time],
            processed_at__isnull=True
        )
        
        processed_count = 0
        
        for activity in unprocessed_activities:
            try:
                # Analyze activity
                analysis = ActivityProcessor.analyze_activity(activity)
                
                # Update activity with recovery time estimate
                recovery_analysis = analysis.get('recovery_analysis', {})
                if recovery_analysis:
                    activity.recovery_time_minutes = recovery_analysis.get('estimated_recovery_hours', 0) * 60
                
                activity.processed_at = timezone.now()
                activity.save()
                
                processed_count += 1
                
                # Create activity insight if it was intense
                if activity.intensity in ['vigorous', 'maximal']:
                    HealthInsight.objects.create(
                        user=self.user,
                        insight_type='achievement',
                        category='activity',
                        title='Intense Workout Completed',
                        description=f'{activity.activity_type.title()} session of {activity.duration_minutes} minutes.',
                        confidence=0.9,
                        start_date=activity.start_time.date(),
                        end_date=activity.start_time.date(),
                        generated_by='system'
                    )
                
            except Exception as e:
                logger.error(f"Error processing activity {activity.id}: {e}")
                continue
        
        return {
            'processed': processed_count,
            'time_range': {
                'start': start_time,
                'end': end_time
            }
        }
    
    def _update_daily_summary(self):
        """Update or create daily summary for today"""
        
        today = timezone.now().date()
        
        # Get or create daily summary
        daily_summary, created = DailySummary.objects.get_or_create(
            user=self.user,
            date=today,
            defaults={'is_complete': False}
        )
        
        # Calculate today's metrics
        activities_today = Activity.objects.filter(
            user=self.user,
            start_time__date=today
        )
        
        sleep_today = SleepSession.objects.filter(
            user=self.user,
            start_time__date=today
        ).first()
        
        heart_rate_today = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__date=today
        )
        
        # Update activity metrics
        if activities_today.exists():
            activity_stats = activities_today.aggregate(
                total_steps=Sum('steps'),
                total_calories=Sum('calories_burned'),
                total_duration=Sum('duration_minutes')
            )
            
            daily_summary.total_steps = activity_stats['total_steps'] or 0
            daily_summary.total_calories = activity_stats['total_calories'] or 0
        
        # Update sleep metrics
        if sleep_today:
            daily_summary.sleep_duration_minutes = sleep_today.duration_minutes
            daily_summary.sleep_score = sleep_today.quality_score
            daily_summary.sleep_efficiency = sleep_today.sleep_efficiency
        
        # Update heart rate metrics
        if heart_rate_today.exists():
            hr_stats = heart_rate_today.aggregate(
                avg=Avg('bpm'),
                min=Min('bpm'),
                max=Max('bpm')
            )
            
            daily_summary.avg_heart_rate = hr_stats['avg']
            daily_summary.min_heart_rate = hr_stats['min']
            daily_summary.max_heart_rate = hr_stats['max']
            
            # Calculate resting heart rate (lowest heart rate during rest/sleep)
            resting_readings = heart_rate_today.filter(
                Q(context='rest') | Q(context='sleep')
            ).order_by('bpm').first()
            
            if resting_readings:
                daily_summary.resting_heart_rate = resting_readings.bpm
        
        # Mark as complete if we have enough data
        has_activity = activities_today.exists()
        has_sleep = sleep_today is not None
        has_heart_rate = heart_rate_today.exists()
        
        daily_summary.is_complete = has_activity and has_sleep and has_heart_rate
        
        daily_summary.save()

    def get_today_steps(self):
        """Get today's steps count"""
        today = timezone.now().date()
        
        try:
            # Try to get from DailySummary
            daily_summary = DailySummary.objects.get(user=self.user, date=today)
            return daily_summary.total_steps or 0
        except DailySummary.DoesNotExist:
            # Calculate from today's activities
            today_activities = Activity.objects.filter(
                user=self.user,
                start_time__date=today
            )
            
            total_steps = 0
            for activity in today_activities:
                if activity.distance_km:
                    # Estimate steps from distance (approx 1312 steps per km)
                    total_steps += int(activity.distance_km * 1312)
            
            return total_steps
    
    def get_current_heart_rate_data(self):
        """Get current heart rate data (NOT recursive)"""
        try:
            # Get most recent heart rate reading
            latest_hr = HeartRateReading.objects.filter(
                user=self.user
            ).order_by('-timestamp').first()
            
            if latest_hr:
                # Get resting heart rate (average of lowest readings from rest/sleep context)
                resting_readings = HeartRateReading.objects.filter(
                    user=self.user,
                    context__in=['rest', 'sleep'],
                    timestamp__date=timezone.now().date()
                )
                avg_resting = resting_readings.aggregate(avg=Avg('bpm'))['avg'] if resting_readings.exists() else None
                
                return {
                    'current': latest_hr.bpm,
                    'resting': avg_resting,
                    'average': self._get_average_heart_rate(),
                    'unit': 'BPM'
                }
        except Exception as e:
            logger.error(f"Error getting heart rate data: {e}")
        
        return None
    
    def _get_average_heart_rate(self):
        """Get average heart rate for today"""
        today = timezone.now().date()
        
        try:
            today_hr = HeartRateReading.objects.filter(
                user=self.user,
                timestamp__date=today
            ).aggregate(avg=Avg('bpm'))['avg']
            
            return today_hr
        except Exception:
            return None
    
    def get_last_sleep_summary(self):
        """Get last sleep data"""
        try:
            last_sleep = SleepSession.objects.filter(user=self.user).order_by('-end_time').first()
            
            if last_sleep:
                return {
                    'duration_minutes': last_sleep.duration_minutes,
                    'score': last_sleep.quality_score,
                    'efficiency': last_sleep.sleep_efficiency
                }
        except Exception as e:
            logger.error(f"Error getting sleep data: {e}")
        
        return None
    
    def get_today_active_minutes(self):
        """Get today's active minutes"""
        today = timezone.now().date()
        
        try:
            today_activities = Activity.objects.filter(
                user=self.user,
                start_time__date=today
            )
            
            total_minutes = today_activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
            return total_minutes
        except Exception:
            return 0
    
    def get_heart_rate_trends(self, days: int = 7):
        """Get heart rate trends"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            heart_rate_data = HeartRateReading.objects.filter(
                user=self.user,
                timestamp__date__range=[start_date, end_date]
            ).extra({'date': "date(timestamp)"}).values('date').annotate(
                avg_bpm=Avg('bpm'),
                min_bpm=Min('bpm'),
                max_bpm=Max('bpm'),
                count=Count('id')
            ).order_by('date')
            
            return list(heart_rate_data)
        except Exception as e:
            logger.error(f"Error getting heart rate trends: {e}")
            return []
    
    def get_steps_trends(self, days: int = 7):
        """Get steps trends"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            steps_data = DailySummary.objects.filter(
                user=self.user,
                date__range=[start_date, end_date]
            ).values('date').annotate(
                steps=Sum('total_steps'),
                calories=Sum('total_calories')
            ).order_by('date')
            
            return list(steps_data)
        except Exception as e:
            logger.error(f"Error getting steps trends: {e}")
            return []
    
    def get_current_health_status(self):
        """Get current health status for dashboard - FIXED with timezone support"""
        user = self.user
        today = timezone.now().date()  # Get timezone-aware date
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Use timezone-aware datetime for filtering
        from django.db.models import F, Func, Value, CharField
        
        # Get recent alerts (last 7 days) - FIXED timezone comparison
        recent_alerts = HealthAlert.objects.filter(
            user=user,
            created_at__date__gte=week_ago
        ).order_by('-created_at')
        
        # Get unread count BEFORE slicing
        unread_count = recent_alerts.filter(is_read=False).count()
        
        # Now slice for the recent alerts list
        recent_alerts_list = list(recent_alerts[:5])
        
        # Get recent insights with timezone-aware filtering
        recent_insights = list(HealthInsight.objects.filter(
            user=user,
            generated_at__date__gte=month_ago  # Use __date lookup for date comparison
        ).order_by('-generated_at')[:5])
        
        # Get active goals with timezone-aware date
        active_goals = list(HealthGoal.objects.filter(
            user=user,
            is_active=True,
            end_date__gte=today
        ).order_by('-created_at'))
        
        # Get today's activities with timezone-aware filtering
        today_activities = list(Activity.objects.filter(
            user=user,
            start_time__date=today  # Use __date lookup
        ).order_by('-start_time')[:10])
        
        # Get today's summary
        try:
            today_summary = DailySummary.objects.get(user=user, date=today)
        except DailySummary.DoesNotExist:
            today_summary = None
        
        # Get last sleep data
        last_sleep = SleepSession.objects.filter(user=user).order_by('-end_time').first()
        
        # Get current status data
        current_status = {
            'steps': self.get_today_steps(),
            'heart_rate': self.get_current_heart_rate_data(),
            'sleep': self.get_last_sleep_summary(),
            'active_minutes': self.get_today_active_minutes(),
        }
        
        return {
            'current_status': current_status,
            'today_summary': today_summary,
            'recent_activities': today_activities,
            'last_sleep': last_sleep,
            'active_goals': active_goals,
            'recent_alerts': {
                'list': recent_alerts_list,
                'unread': unread_count,
            },
            'recent_insights': recent_insights,
            'trends': {
                'heart_rate': self.get_heart_rate_trends(),
                'steps': self.get_steps_trends(),
            }
        }

    def get_health_trends(self, metric: str = None, days: int = 30) -> Dict[str, Any]:
        """Get health trends for specified metric or all metrics"""
        
        trends = self.analyzer.analyze_health_trends(days=days)
        
        if metric:
            # Return specific metric trend
            metric_trend = trends.get('trends', {}).get(metric)
            if metric_trend:
                return {
                    'metric': metric,
                    'period_days': days,
                    'trend': metric_trend
                }
            else:
                return {
                    'error': f'Metric {metric} not found in trends data',
                    'available_metrics': list(trends.get('trends', {}).keys())
                }
        
        return trends
    
    def generate_health_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive health report for date range"""
        
        report = {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': (end_date - start_date).days
            },
            'summary': {},
            'activity_analysis': {},
            'sleep_analysis': {},
            'heart_health_analysis': {},
            'insights': [],
            'recommendations': []
        }
        
        # Get daily summaries for period
        daily_summaries = DailySummary.objects.filter(
            user=self.user,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        if not daily_summaries.exists():
            report['error'] = 'No health data available for this period'
            return report
        
        # Calculate summary statistics
        activity_days = sum(1 for d in daily_summaries if d.total_steps > 5000)
        good_sleep_days = sum(1 for d in daily_summaries if d.sleep_score and d.sleep_score >= 70)
        
        avg_steps = daily_summaries.aggregate(avg=Avg('total_steps'))['avg'] or 0
        avg_sleep = daily_summaries.aggregate(avg=Avg('sleep_duration_minutes'))['avg'] or 0
        avg_hr = daily_summaries.aggregate(avg=Avg('avg_heart_rate'))['avg'] or 0
        
        report['summary'] = {
            'total_days': daily_summaries.count(),
            'active_days': activity_days,
            'good_sleep_days': good_sleep_days,
            'average_daily_steps': round(avg_steps),
            'average_sleep_hours': round(avg_sleep / 60, 1),
            'average_heart_rate': round(avg_hr, 1),
            'activity_percentage': round((activity_days / daily_summaries.count()) * 100, 1),
            'sleep_quality_percentage': round((good_sleep_days / daily_summaries.count()) * 100, 1) if daily_summaries.count() > 0 else 0
        }
        
        # Activity analysis
        activities = Activity.objects.filter(
            user=self.user,
            start_time__date__range=[start_date, end_date]
        )
        
        if activities.exists():
            activity_by_type = activities.values('activity_type').annotate(
                count=Count('id'),
                total_duration=Sum('duration_minutes'),
                total_calories=Sum('calories_burned')
            ).order_by('-total_duration')
            
            report['activity_analysis'] = {
                'total_activities': activities.count(),
                'total_duration_hours': round(activities.aggregate(total=Sum('duration_minutes'))['total'] or 0 / 60, 1),
                'total_calories': round(activities.aggregate(total=Sum('calories_burned'))['total'] or 0, 1),
                'by_type': list(activity_by_type),
                'most_common_activity': activity_by_type.first()['activity_type'] if activity_by_type else None
            }
        
        # Sleep analysis
        sleep_sessions = SleepSession.objects.filter(
            user=self.user,
            start_time__date__range=[start_date, end_date]
        )
        
        if sleep_sessions.exists():
            sleep_stats = sleep_sessions.aggregate(
                avg_duration=Avg('duration_minutes'),
                avg_score=Avg('quality_score'),
                avg_efficiency=Avg('sleep_efficiency')
            )
            
            report['sleep_analysis'] = {
                'total_sessions': sleep_sessions.count(),
                'average_duration_hours': round((sleep_stats['avg_duration'] or 0) / 60, 1),
                'average_quality_score': round(sleep_stats['avg_score'] or 0, 1),
                'average_efficiency': round(sleep_stats['avg_efficiency'] or 0, 1),
                'consistency': self._calculate_sleep_consistency(sleep_sessions)
            }
        
        # Heart health analysis
        heart_rate_readings = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__date__range=[start_date, end_date]
        )
        
        if heart_rate_readings.exists():
            hr_stats = heart_rate_readings.aggregate(
                avg=Avg('bpm'),
                min=Min('bpm'),
                max=Max('bpm')
            )
            
            # Calculate resting HR from sleep/rest context
            resting_readings = heart_rate_readings.filter(
                Q(context='rest') | Q(context='sleep')
            )
            
            avg_resting = resting_readings.aggregate(avg=Avg('bpm'))['avg'] if resting_readings.exists() else None
            
            report['heart_health_analysis'] = {
                'total_readings': heart_rate_readings.count(),
                'average_bpm': round(hr_stats['avg'] or 0, 1),
                'minimum_bpm': hr_stats['min'],
                'maximum_bpm': hr_stats['max'],
                'average_resting_bpm': round(avg_resting, 1) if avg_resting else None,
                'variability': self._calculate_heart_rate_variability(heart_rate_readings)
            }
        
        # Generate insights
        report['insights'] = self._generate_report_insights(report)
        
        # Generate recommendations
        report['recommendations'] = self._generate_report_recommendations(report)
        
        return report
    
    def _calculate_sleep_consistency(self, sleep_sessions) -> Dict[str, Any]:
        """Calculate sleep consistency metrics"""
        
        if not sleep_sessions.exists():
            return {'status': 'no_data'}
        
        durations = [s.duration_minutes for s in sleep_sessions]
        avg_duration = np.mean(durations)
        std_duration = np.std(durations)
        
        # Calculate bedtime consistency
        bedtimes = [s.start_time.hour * 60 + s.start_time.minute for s in sleep_sessions]
        std_bedtime = np.std(bedtimes) if len(bedtimes) > 1 else 0
        
        consistency_score = max(0, 100 - ((std_duration / 60) + (std_bedtime / 30)))
        
        return {
            'duration_consistency': 'high' if std_duration < 60 else 'medium' if std_duration < 120 else 'low',
            'bedtime_consistency': 'high' if std_bedtime < 30 else 'medium' if std_bedtime < 60 else 'low',
            'consistency_score': round(consistency_score, 1),
            'duration_std_minutes': round(std_duration, 1),
            'bedtime_std_minutes': round(std_bedtime, 1)
        }
    
    def _calculate_heart_rate_variability(self, heart_rate_readings) -> Dict[str, Any]:
        """Calculate heart rate variability metrics"""
        
        if heart_rate_readings.count() < 100:
            return {'status': 'insufficient_data'}
        
        # Simple HRV calculation (would be more complex in production)
        readings = list(heart_rate_readings.order_by('timestamp'))
        
        rr_intervals = []
        for i in range(1, len(readings)):
            time_diff = (readings[i].timestamp - readings[i-1].timestamp).total_seconds()
            rr_intervals.append(time_diff)
        
        if len(rr_intervals) < 50:
            return {'status': 'insufficient_intervals'}
        
        rr_array = np.array(rr_intervals)
        
        # Calculate RMSSD
        differences = np.diff(rr_array)
        squared_diff = np.square(differences)
        mean_squared = np.mean(squared_diff)
        rmssd = np.sqrt(mean_squared) * 1000  # Convert to milliseconds
        
        # Calculate SDNN
        sdnn = np.std(rr_array) * 1000
        
        return {
            'rmssd_ms': round(rmssd, 1),
            'sdnn_ms': round(sdnn, 1),
            'hrv_status': 'good' if rmssd > 50 else 'fair' if rmssd > 30 else 'poor',
            'interpretation': 'Higher values indicate better cardiovascular fitness and recovery'
        }
    
    def _generate_report_insights(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from report data"""
        
        insights = []
        summary = report.get('summary', {})
        
        # Activity insights
        activity_percentage = summary.get('activity_percentage', 0)
        if activity_percentage >= 80:
            insights.append({
                'type': 'achievement',
                'category': 'activity',
                'title': 'Highly Active Period',
                'description': f'Active on {activity_percentage}% of days during this period.',
                'confidence': 0.9
            })
        elif activity_percentage < 50:
            insights.append({
                'type': 'recommendation',
                'category': 'activity',
                'title': 'Increase Activity Frequency',
                'description': f'Only active on {activity_percentage}% of days. Aim for at least 5 active days per week.',
                'confidence': 0.8
            })
        
        # Sleep insights
        sleep_quality_percentage = summary.get('sleep_quality_percentage', 0)
        if sleep_quality_percentage >= 80:
            insights.append({
                'type': 'achievement',
                'category': 'sleep',
                'title': 'Consistent Good Sleep',
                'description': f'Good sleep quality on {sleep_quality_percentage}% of nights.',
                'confidence': 0.9
            })
        
        avg_sleep_hours = summary.get('average_sleep_hours', 0)
        if avg_sleep_hours < 7:
            insights.append({
                'type': 'recommendation',
                'category': 'sleep',
                'title': 'Increase Sleep Duration',
                'description': f'Average sleep of {avg_sleep_hours} hours per night. Aim for 7-9 hours.',
                'confidence': 0.9
            })
        
        return insights
    
    def _generate_report_recommendations(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations from report data"""
        
        recommendations = []
        summary = report.get('summary', {})
        
        avg_steps = summary.get('average_daily_steps', 0)
        if avg_steps < 8000:
            recommendations.append({
                'category': 'activity',
                'title': 'Increase Daily Steps',
                'description': f'Current average: {avg_steps:,.0f} steps. Aim for at least 8,000 steps daily.',
                'priority': 'medium',
                'actions': [
                    'Take short walking breaks every hour',
                    'Park farther away or get off transit one stop early',
                    'Take stairs instead of elevators'
                ]
            })
        
        avg_sleep = summary.get('average_sleep_hours', 0)
        if avg_sleep < 7:
            recommendations.append({
                'category': 'sleep',
                'title': 'Prioritize Sleep Duration',
                'description': f'Average sleep: {avg_sleep:.1f} hours. Target: 7-9 hours per night.',
                'priority': 'high',
                'actions': [
                    'Establish consistent bedtime routine',
                    'Limit screen time 1 hour before bed',
                    'Create optimal sleep environment (cool, dark, quiet)'
                ]
            })
        
        # Check for activity variety
        activity_analysis = report.get('activity_analysis', {})
        if activity_analysis:
            by_type = activity_analysis.get('by_type', [])
            if len(by_type) < 3:
                recommendations.append({
                    'category': 'activity',
                    'title': 'Diversify Activities',
                    'description': 'Limited variety in activity types. Cross-training improves overall fitness.',
                    'priority': 'low',
                    'actions': [
                        'Try one new activity each week',
                        'Balance cardio, strength, and flexibility training',
                        'Join different fitness classes or groups'
                    ]
                })
        
        return recommendations
    
    def track_health_goal(self, goal_id: str, date: datetime = None) -> Dict[str, Any]:
        """Track progress towards a health goal"""
        
        if not date:
            date = timezone.now().date()
        
        try:
            goal = HealthGoal.objects.get(id=goal_id, user=self.user)
        except HealthGoal.DoesNotExist:
            return {'error': 'Goal not found'}
        
        # Calculate current value based on goal type
        current_value = 0
        
        if goal.goal_type == 'steps':
            daily_summary = DailySummary.objects.filter(
                user=self.user,
                date=date
            ).first()
            current_value = daily_summary.total_steps if daily_summary else 0
        
        elif goal.goal_type == 'sleep':
            sleep_session = SleepSession.objects.filter(
                user=self.user,
                start_time__date=date
            ).first()
            current_value = sleep_session.duration_minutes if sleep_session else 0
        
        elif goal.goal_type == 'activity':
            activities = Activity.objects.filter(
                user=self.user,
                start_time__date=date
            )
            current_value = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
        
        elif goal.goal_type == 'calories':
            activities = Activity.objects.filter(
                user=self.user,
                start_time__date=date
            )
            current_value = activities.aggregate(total=Sum('calories_burned'))['total'] or 0
        
        # Update goal progress
        goal.current_value = current_value
        goal.save()
        
        # Check if goal was met today
        goal_met = current_value >= goal.target_value
        
        # Update streak
        if goal_met:
            goal.current_streak += 1
            if goal.current_streak > goal.longest_streak:
                goal.longest_streak = goal.current_streak
        else:
            goal.current_streak = 0
        
        goal.save()
        
        return {
            'goal_id': goal_id,
            'goal_name': goal.name,
            'date': date,
            'target_value': goal.target_value,
            'current_value': current_value,
            'progress_percentage': goal.progress_percentage,
            'goal_met': goal_met,
            'current_streak': goal.current_streak,
            'longest_streak': goal.longest_streak
        }