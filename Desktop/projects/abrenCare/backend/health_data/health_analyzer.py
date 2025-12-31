import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from django.db.models import Avg, Sum, Count, Q, Max, Min

from .models import (
    HeartRateReading, SleepSession, Activity, DailySummary,
    HealthGoal, HealthAlert, HealthInsight
)
from .heart_rate_processor import HeartRateProcessor
from .sleep_processor import SleepProcessor
from .activity_processor import ActivityProcessor

logger = logging.getLogger(__name__)


class HealthAnalyzer:
    """Main health analyzer that coordinates all health analysis"""
    
    def __init__(self, user):
        self.user = user
        self.now = timezone.now()
    
    def generate_daily_insights(self, date: datetime = None) -> List[Dict[str, Any]]:
        """Generate daily health insights"""
        
        if not date:
            date = self.now.date()
        
        insights = []
        
        # Get daily summary
        daily_summary = DailySummary.objects.filter(
            user=self.user,
            date=date
        ).first()
        
        if not daily_summary:
            # Create basic daily summary
            daily_summary = self._create_daily_summary(date)
        
        # Analyze different health aspects
        insights.extend(self._analyze_activity_insights(daily_summary, date))
        insights.extend(self._analyze_sleep_insights(daily_summary, date))
        insights.extend(self._analyze_heart_rate_insights(daily_summary, date))
        insights.extend(self._analyze_overall_health_insights(daily_summary, date))
        
        # Generate recommendations
        recommendations = self._generate_daily_recommendations(daily_summary, insights)
        insights.extend(recommendations)
        
        # Save insights to database
        self._save_insights_to_database(insights, date)
        
        return insights
    
    def _create_daily_summary(self, date: datetime) -> DailySummary:
        """Create a daily summary from raw data"""
        
        # Calculate metrics from raw data
        activities = Activity.objects.filter(
            user=self.user,
            start_time__date=date
        )
        
        sleep_sessions = SleepSession.objects.filter(
            user=self.user,
            start_time__date=date
        )
        
        heart_rate_readings = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__date=date
        )
        
        # Calculate activity metrics
        total_steps = activities.aggregate(total=Sum('steps'))['total'] or 0
        total_calories = activities.aggregate(total=Sum('calories_burned'))['total'] or 0
        
        # Calculate heart rate metrics
        heart_rate_stats = heart_rate_readings.aggregate(
            avg=Avg('bpm'),
            min=Min('bpm'),
            max=Max('bpm')
        )
        
        # Calculate sleep metrics
        sleep_duration = sleep_sessions.aggregate(total=Sum('duration_minutes'))['total']
        sleep_score = sleep_sessions.aggregate(avg=Avg('quality_score'))['avg']
        
        # Create daily summary
        daily_summary = DailySummary.objects.create(
            user=self.user,
            date=date,
            total_steps=total_steps,
            total_calories=total_calories,
            avg_heart_rate=heart_rate_stats['avg'],
            min_heart_rate=heart_rate_stats['min'],
            max_heart_rate=heart_rate_stats['max'],
            sleep_duration_minutes=sleep_duration,
            sleep_score=sleep_score,
            is_complete=False
        )
        
        return daily_summary
    
    def _analyze_activity_insights(self, daily_summary: DailySummary, date: datetime) -> List[Dict[str, Any]]:
        """Generate activity-related insights"""
        
        insights = []
        
        # Step goal analysis
        step_goal = 10000  # Default goal, should be user-specific
        steps = daily_summary.total_steps or 0
        step_percentage = (steps / step_goal) * 100
        
        if steps >= step_goal:
            insights.append({
                'type': 'achievement',
                'category': 'activity',
                'title': 'Step Goal Achieved!',
                'description': f'You reached {steps:,} steps today, exceeding your daily goal of {step_goal:,} steps.',
                'confidence': 1.0,
                'data_points': {
                    'steps': steps,
                    'goal': step_goal,
                    'percentage': round(step_percentage, 1)
                }
            })
        elif steps >= step_goal * 0.8:
            insights.append({
                'type': 'progress',
                'category': 'activity',
                'title': 'Close to Step Goal',
                'description': f'You\'re at {steps:,} steps, {round(step_goal - steps):,} steps away from your daily goal.',
                'confidence': 0.9,
                'data_points': {
                    'steps': steps,
                    'goal': step_goal,
                    'remaining': step_goal - steps
                }
            })
        elif steps < step_goal * 0.5:
            insights.append({
                'type': 'recommendation',
                'category': 'activity',
                'title': 'Increase Daily Activity',
                'description': f'You\'ve taken {steps:,} steps today. Consider adding a walk to reach your goal.',
                'confidence': 0.8,
                'data_points': {
                    'steps': steps,
                    'goal': step_goal,
                    'percentage': round(step_percentage, 1)
                }
            })
        
        # Activity consistency analysis
        activities_today = Activity.objects.filter(
            user=self.user,
            start_time__date=date
        ).count()
        
        if activities_today == 0:
            insights.append({
                'type': 'recommendation',
                'category': 'activity',
                'title': 'Time for Movement',
                'description': 'No recorded activities today. Consider adding some physical movement.',
                'confidence': 0.9,
                'data_points': {'activities_count': 0}
            })
        
        return insights
    
    def _analyze_sleep_insights(self, daily_summary: DailySummary, date: datetime) -> List[Dict[str, Any]]:
        """Generate sleep-related insights"""
        
        insights = []
        
        sleep_duration = daily_summary.sleep_duration_minutes
        sleep_score = daily_summary.sleep_score
        
        if sleep_duration:
            sleep_hours = sleep_duration / 60
            
            # Sleep duration analysis
            if sleep_hours >= 7 and sleep_hours <= 9:
                insights.append({
                    'type': 'achievement',
                    'category': 'sleep',
                    'title': 'Optimal Sleep Duration',
                    'description': f'You slept {sleep_hours:.1f} hours, within the recommended 7-9 hour range.',
                    'confidence': 1.0,
                    'data_points': {
                        'hours': round(sleep_hours, 1),
                        'minutes': sleep_duration,
                        'optimal_range': '7-9 hours'
                    }
                })
            elif sleep_hours < 6:
                insights.append({
                    'type': 'warning',
                    'category': 'sleep',
                    'title': 'Insufficient Sleep',
                    'description': f'You slept {sleep_hours:.1f} hours, below the recommended minimum of 7 hours.',
                    'confidence': 0.9,
                    'data_points': {
                        'hours': round(sleep_hours, 1),
                        'recommended_minimum': 7,
                        'deficit_hours': round(7 - sleep_hours, 1)
                    }
                })
            elif sleep_hours > 9:
                insights.append({
                    'type': 'pattern',
                    'category': 'sleep',
                    'title': 'Extended Sleep Duration',
                    'description': f'You slept {sleep_hours:.1f} hours, above the recommended range.',
                    'confidence': 0.8,
                    'data_points': {
                        'hours': round(sleep_hours, 1),
                        'optimal_range': '7-9 hours',
                        'excess_hours': round(sleep_hours - 9, 1)
                    }
                })
        
        # Sleep quality analysis
        if sleep_score:
            if sleep_score >= 85:
                insights.append({
                    'type': 'achievement',
                    'category': 'sleep',
                    'title': 'Excellent Sleep Quality',
                    'description': f'Your sleep quality score of {sleep_score:.0f}/100 indicates restful sleep.',
                    'confidence': 0.9,
                    'data_points': {'score': round(sleep_score, 1)}
                })
            elif sleep_score < 60:
                insights.append({
                    'type': 'recommendation',
                    'category': 'sleep',
                    'title': 'Improve Sleep Quality',
                    'description': f'Your sleep quality score of {sleep_score:.0f}/100 suggests room for improvement.',
                    'confidence': 0.8,
                    'data_points': {'score': round(sleep_score, 1)}
                })
        
        return insights
    
    def _analyze_heart_rate_insights(self, daily_summary: DailySummary, date: datetime) -> List[Dict[str, Any]]:
        """Generate heart rate-related insights"""
        
        insights = []
        
        avg_hr = daily_summary.avg_heart_rate
        resting_hr = daily_summary.resting_heart_rate
        
        if avg_hr:
            # Average heart rate analysis
            if avg_hr < 60:
                insights.append({
                    'type': 'pattern',
                    'category': 'heart',
                    'title': 'Low Average Heart Rate',
                    'description': f'Your average heart rate of {avg_hr:.0f} BPM is lower than typical.',
                    'confidence': 0.8,
                    'data_points': {
                        'average_bpm': round(avg_hr, 1),
                        'typical_range': '60-100 BPM'
                    }
                })
            elif avg_hr > 100:
                insights.append({
                    'type': 'warning',
                    'category': 'heart',
                    'title': 'Elevated Average Heart Rate',
                    'description': f'Your average heart rate of {avg_hr:.0f} BPM is higher than typical.',
                    'confidence': 0.8,
                    'data_points': {
                        'average_bpm': round(avg_hr, 1),
                        'typical_range': '60-100 BPM'
                    }
                })
        
        if resting_hr:
            # Resting heart rate analysis
            if resting_hr < 60:
                insights.append({
                    'type': 'achievement',
                    'category': 'heart',
                    'title': 'Excellent Resting Heart Rate',
                    'description': f'Your resting heart rate of {resting_hr:.0f} BPM indicates good cardiovascular fitness.',
                    'confidence': 0.9,
                    'data_points': {
                        'resting_bpm': resting_hr,
                        'optimal_range': '<60 BPM'
                    }
                })
            elif resting_hr > 80:
                insights.append({
                    'type': 'recommendation',
                    'category': 'heart',
                    'title': 'Monitor Resting Heart Rate',
                    'description': f'Your resting heart rate of {resting_hr:.0f} BPM is above optimal levels.',
                    'confidence': 0.8,
                    'data_points': {
                        'resting_bpm': resting_hr,
                        'optimal_range': '50-70 BPM'
                    }
                })
        
        # Heart rate variability analysis
        hrv = daily_summary.heart_rate_variability
        if hrv:
            if hrv < 20:
                insights.append({
                    'type': 'pattern',
                    'category': 'heart',
                    'title': 'Low Heart Rate Variability',
                    'description': f'Your HRV of {hrv:.0f} ms may indicate increased stress or fatigue.',
                    'confidence': 0.7,
                    'data_points': {
                        'hrv_ms': round(hrv, 1),
                        'optimal_range': '>50 ms'
                    }
                })
        
        return insights
    
    def _analyze_overall_health_insights(self, daily_summary: DailySummary, date: datetime) -> List[Dict[str, Any]]:
        """Generate overall health insights"""
        
        insights = []
        
        # Calculate overall health score
        health_score = self._calculate_daily_health_score(daily_summary)
        
        if health_score:
            daily_summary.overall_score = health_score
            
            if health_score >= 80:
                insights.append({
                    'type': 'achievement',
                    'category': 'overall',
                    'title': 'Excellent Health Day',
                    'description': f'Your overall health score of {health_score:.0f}/100 indicates a very healthy day!',
                    'confidence': 0.9,
                    'data_points': {'score': round(health_score, 1)}
                })
            elif health_score >= 60:
                insights.append({
                    'type': 'progress',
                    'category': 'overall',
                    'title': 'Good Health Day',
                    'description': f'Your overall health score of {health_score:.0f}/100 shows a solid day.',
                    'confidence': 0.8,
                    'data_points': {'score': round(health_score, 1)}
                })
            else:
                insights.append({
                    'type': 'recommendation',
                    'category': 'overall',
                    'title': 'Room for Improvement',
                    'description': f'Your overall health score of {health_score:.0f}/100 suggests areas to focus on.',
                    'confidence': 0.8,
                    'data_points': {'score': round(health_score, 1)}
                })
        
        # Check for complete data
        if not daily_summary.is_complete:
            insights.append({
                'type': 'info',
                'category': 'overall',
                'title': 'Incomplete Data',
                'description': 'Some health metrics may be missing for today.',
                'confidence': 0.7,
                'data_points': {'is_complete': False}
            })
        
        daily_summary.save()
        
        return insights
    
    def _calculate_daily_health_score(self, daily_summary: DailySummary) -> Optional[float]:
        """Calculate overall daily health score"""
        
        weights = {
            'activity': 0.35,
            'sleep': 0.35,
            'heart': 0.20,
            'recovery': 0.10
        }
        
        scores = {}
        
        # Activity score (based on steps)
        steps = daily_summary.total_steps or 0
        step_goal = 10000
        scores['activity'] = min(100, (steps / step_goal) * 100)
        
        # Sleep score
        sleep_duration = daily_summary.sleep_duration_minutes
        sleep_score = daily_summary.sleep_score
        
        if sleep_score:
            scores['sleep'] = sleep_score
        elif sleep_duration:
            # Estimate sleep score from duration
            sleep_hours = sleep_duration / 60
            if 7 <= sleep_hours <= 9:
                scores['sleep'] = 90
            elif 6 <= sleep_hours < 7 or 9 < sleep_hours <= 10:
                scores['sleep'] = 70
            elif 5 <= sleep_hours < 6 or 10 < sleep_hours <= 11:
                scores['sleep'] = 50
            else:
                scores['sleep'] = 30
        else:
            scores['sleep'] = 50  # Default if no sleep data
        
        # Heart score
        resting_hr = daily_summary.resting_heart_rate
        if resting_hr:
            if resting_hr < 60:
                scores['heart'] = 90
            elif resting_hr < 70:
                scores['heart'] = 80
            elif resting_hr < 80:
                scores['heart'] = 70
            else:
                scores['heart'] = 50
        else:
            scores['heart'] = 70  # Default if no HR data
        
        # Recovery score
        recovery_score = daily_summary.recovery_score
        if recovery_score:
            scores['recovery'] = recovery_score
        else:
            scores['recovery'] = 75  # Default
        
        # Calculate weighted score
        total_score = sum(scores[category] * weight for category, weight in weights.items())
        
        return round(total_score, 1)
    
    def _generate_daily_recommendations(self, daily_summary: DailySummary, insights: List[Dict]) -> List[Dict[str, Any]]:
        """Generate personalized daily recommendations"""
        
        recommendations = []
        
        # Analyze insights to generate recommendations
        activity_insights = [i for i in insights if i['category'] == 'activity']
        sleep_insights = [i for i in insights if i['category'] == 'sleep']
        heart_insights = [i for i in insights if i['category'] == 'heart']
        
        # Activity recommendations
        low_activity = any(i['type'] == 'recommendation' for i in activity_insights)
        if low_activity:
            recommendations.append({
                'type': 'recommendation',
                'category': 'activity',
                'title': 'Daily Movement Goal',
                'description': 'Aim for at least 30 minutes of moderate activity today.',
                'confidence': 0.9,
                'action_items': [
                    'Take a 15-minute walk after meals',
                    'Use stairs instead of elevator',
                    'Do 10 minutes of stretching'
                ],
                'priority': 'high'
            })
        
        # Sleep recommendations
        poor_sleep = any(i['type'] in ['warning', 'recommendation'] for i in sleep_insights)
        if poor_sleep:
            recommendations.append({
                'type': 'recommendation',
                'category': 'sleep',
                'title': 'Improve Sleep Tonight',
                'description': 'Focus on sleep hygiene for better rest.',
                'confidence': 0.8,
                'action_items': [
                    'Avoid screens 1 hour before bed',
                    'Keep bedroom cool and dark',
                    'Establish consistent bedtime'
                ],
                'priority': 'medium'
            })
        
        # Heart health recommendations
        elevated_hr = any(i['type'] == 'warning' for i in heart_insights)
        if elevated_hr:
            recommendations.append({
                'type': 'recommendation',
                'category': 'heart',
                'title': 'Heart Health Focus',
                'description': 'Consider activities that support cardiovascular health.',
                'confidence': 0.7,
                'action_items': [
                    'Practice deep breathing exercises',
                    'Stay well hydrated',
                    'Monitor stress levels'
                ],
                'priority': 'medium'
            })
        
        return recommendations
    
    def _save_insights_to_database(self, insights: List[Dict], date: datetime):
        """Save generated insights to database"""
        
        for insight in insights:
            HealthInsight.objects.create(
                user=self.user,
                insight_type=insight['type'],
                category=insight['category'],
                title=insight['title'],
                description=insight['description'],
                confidence=insight.get('confidence', 0.8),
                data_points=insight.get('data_points', {}),
                start_date=date,
                end_date=date,
                action_items=insight.get('action_items', []),
                recommendations=insight.get('recommendations', []),
                generated_by='system'
            )
    
    def analyze_health_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze health trends over time"""
        
        end_date = self.now.date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily summaries for the period
        daily_summaries = DailySummary.objects.filter(
            user=self.user,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        if not daily_summaries.exists():
            return {'status': 'no_data', 'message': f'No health data for the last {days} days'}
        
        # Extract trends for different metrics
        trends = {
            'steps': self._extract_trend(daily_summaries, 'total_steps'),
            'sleep_duration': self._extract_trend(daily_summaries, 'sleep_duration_minutes'),
            'heart_rate': self._extract_trend(daily_summaries, 'avg_heart_rate'),
            'overall_score': self._extract_trend(daily_summaries, 'overall_score')
        }
        
        # Calculate consistency scores
        consistency = self._calculate_consistency_scores(daily_summaries)
        
        # Identify patterns
        patterns = self._identify_health_patterns(daily_summaries)
        
        # Generate trend insights
        trend_insights = self._generate_trend_insights(trends, consistency, patterns)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'trends': trends,
            'consistency': consistency,
            'patterns': patterns,
            'insights': trend_insights,
            'summary': self._generate_trend_summary(trends, consistency)
        }
    
    def _extract_trend(self, daily_summaries, field: str) -> Dict[str, Any]:
        """Extract trend for a specific field"""
        
        values = []
        dates = []
        
        for summary in daily_summaries:
            value = getattr(summary, field)
            if value is not None:
                values.append(float(value))
                dates.append(summary.date)
        
        if len(values) < 2:
            return {'status': 'insufficient_data', 'count': len(values)}
        
        # Calculate basic statistics
        avg_value = np.mean(values)
        std_value = np.std(values)
        
        # Calculate trend using linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        # Fit linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine trend direction
        if slope > 0 and r_squared > 0.3:
            direction = 'increasing'
        elif slope < 0 and r_squared > 0.3:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # Calculate percentage change
        if len(values) >= 2:
            first_value = values[0]
            last_value = values[-1]
            if first_value != 0:
                percentage_change = ((last_value - first_value) / first_value) * 100
            else:
                percentage_change = 0
        else:
            percentage_change = None
        
        return {
            'average': round(avg_value, 2),
            'standard_deviation': round(std_value, 2),
            'trend_direction': direction,
            'trend_strength': round(r_squared, 3),
            'slope': round(slope, 4),
            'percentage_change': round(percentage_change, 2) if percentage_change is not None else None,
            'data_points': len(values),
            'current_value': values[-1] if values else None,
            'min_value': min(values) if values else None,
            'max_value': max(values) if values else None
        }
    
    def _calculate_consistency_scores(self, daily_summaries) -> Dict[str, Any]:
        """Calculate consistency scores for different metrics"""
        
        consistency = {}
        
        # Steps consistency
        steps_values = [s.total_steps for s in daily_summaries if s.total_steps]
        if steps_values:
            steps_std = np.std(steps_values)
            consistency['steps'] = {
                'score': max(0, 100 - (steps_std / 2000 * 100)),  # Lower std = higher score
                'std': round(steps_std, 1),
                'interpretation': 'high' if steps_std < 1000 else 'medium' if steps_std < 2000 else 'low'
            }
        
        # Sleep consistency
        sleep_values = [s.sleep_duration_minutes for s in daily_summaries if s.sleep_duration_minutes]
        if sleep_values:
            sleep_std = np.std(sleep_values)
            consistency['sleep'] = {
                'score': max(0, 100 - (sleep_std / 120 * 100)),  # Lower std = higher score
                'std': round(sleep_std, 1),
                'interpretation': 'high' if sleep_std < 60 else 'medium' if sleep_std < 120 else 'low'
            }
        
        # Bedtime consistency (if we have sleep session data)
        sleep_sessions = SleepSession.objects.filter(
            user=self.user,
            start_time__date__range=[daily_summaries.first().date, daily_summaries.last().date]
        )
        
        if sleep_sessions.exists():
            bedtimes = [s.start_time.hour * 60 + s.start_time.minute for s in sleep_sessions]
            bedtime_std = np.std(bedtimes) if bedtimes else 0
            consistency['bedtime'] = {
                'score': max(0, 100 - (bedtime_std / 60 * 100)),
                'std_minutes': round(bedtime_std, 1),
                'interpretation': 'high' if bedtime_std < 30 else 'medium' if bedtime_std < 60 else 'low'
            }
        
        return consistency
    
    def _identify_health_patterns(self, daily_summaries) -> List[Dict[str, Any]]:
        """Identify patterns in health data"""
        
        patterns = []
        
        # Weekend vs weekday patterns
        weekday_steps = []
        weekend_steps = []
        
        for summary in daily_summaries:
            weekday = summary.date.weekday()  # Monday=0, Sunday=6
            if weekday < 5:  # Monday-Friday
                if summary.total_steps:
                    weekday_steps.append(summary.total_steps)
            else:  # Saturday-Sunday
                if summary.total_steps:
                    weekend_steps.append(summary.total_steps)
        
        if weekday_steps and weekend_steps:
            avg_weekday = np.mean(weekday_steps)
            avg_weekend = np.mean(weekend_steps)
            
            if avg_weekend - avg_weekday > 2000:
                patterns.append({
                    'type': 'weekend_activity_surge',
                    'description': 'Significantly more active on weekends',
                    'difference': round(avg_weekend - avg_weekday),
                    'interpretation': 'May indicate sedentary work week'
                })
            elif avg_weekday - avg_weekend > 2000:
                patterns.append({
                    'type': 'weekend_activity_dip',
                    'description': 'Less active on weekends',
                    'difference': round(avg_weekday - avg_weekend),
                    'interpretation': 'Consider adding weekend activities'
                })
        
        # Sleep patterns
        sleep_durations = [s.sleep_duration_minutes for s in daily_summaries if s.sleep_duration_minutes]
        if sleep_durations:
            avg_sleep = np.mean(sleep_durations)
            if avg_sleep < 420:  # Less than 7 hours average
                patterns.append({
                    'type': 'chronic_sleep_deficit',
                    'description': 'Consistently getting less than 7 hours of sleep',
                    'average_hours': round(avg_sleep / 60, 1),
                    'interpretation': 'Consider prioritizing sleep duration'
                })
        
        return patterns
    
    def _generate_trend_insights(self, trends: Dict, consistency: Dict, patterns: List) -> List[Dict[str, Any]]:
        """Generate insights from trends"""
        
        insights = []
        
        # Step trend insights
        steps_trend = trends.get('steps', {})
        if steps_trend.get('trend_direction') == 'increasing' and steps_trend.get('percentage_change', 0) > 10:
            insights.append({
                'type': 'achievement',
                'category': 'activity',
                'title': 'Improving Activity Level',
                'description': f'Your step count has increased by {steps_trend["percentage_change"]:.1f}% over this period.',
                'confidence': 0.9
            })
        elif steps_trend.get('trend_direction') == 'decreasing' and steps_trend.get('percentage_change', 0) < -10:
            insights.append({
                'type': 'warning',
                'category': 'activity',
                'title': 'Declining Activity Level',
                'description': f'Your step count has decreased by {abs(steps_trend["percentage_change"]):.1f}% over this period.',
                'confidence': 0.8
            })
        
        # Sleep trend insights
        sleep_trend = trends.get('sleep_duration', {})
        if sleep_trend.get('trend_direction') == 'increasing' and sleep_trend.get('percentage_change', 0) > 10:
            insights.append({
                'type': 'achievement',
                'category': 'sleep',
                'title': 'Improving Sleep Habits',
                'description': 'You\'re consistently getting more sleep over time.',
                'confidence': 0.9
            })
        
        # Consistency insights
        steps_consistency = consistency.get('steps', {})
        if steps_consistency.get('interpretation') == 'high':
            insights.append({
                'type': 'pattern',
                'category': 'activity',
                'title': 'Consistent Activity Level',
                'description': 'You maintain very consistent daily step counts.',
                'confidence': 0.8
            })
        
        # Pattern insights
        for pattern in patterns:
            if pattern['type'] == 'weekend_activity_dip':
                insights.append({
                    'type': 'recommendation',
                    'category': 'activity',
                    'title': 'Weekend Activity Opportunity',
                    'description': 'Consider adding more movement to your weekends.',
                    'confidence': 0.7
                })
            elif pattern['type'] == 'chronic_sleep_deficit':
                insights.append({
                    'type': 'recommendation',
                    'category': 'sleep',
                    'title': 'Prioritize Sleep Duration',
                    'description': 'Aim for at least 7 hours of sleep each night.',
                    'confidence': 0.9
                })
        
        return insights
    
    def _generate_trend_summary(self, trends: Dict, consistency: Dict) -> Dict[str, Any]:
        """Generate summary of health trends"""
        
        summary = {
            'overall_trend': 'improving',
            'key_strengths': [],
            'areas_for_improvement': [],
            'recommendations': []
        }
        
        # Evaluate overall trend
        improving_count = 0
        declining_count = 0
        
        for metric, trend in trends.items():
            if trend.get('trend_direction') == 'increasing' and metric != 'heart_rate':
                improving_count += 1
            elif trend.get('trend_direction') == 'decreasing':
                declining_count += 1
        
        if improving_count > declining_count:
            summary['overall_trend'] = 'improving'
        elif declining_count > improving_count:
            summary['overall_trend'] = 'declining'
        else:
            summary['overall_trend'] = 'stable'
        
        # Identify strengths
        steps_trend = trends.get('steps', {})
        if steps_trend.get('trend_direction') == 'increasing':
            summary['key_strengths'].append('Increasing physical activity')
        
        sleep_trend = trends.get('sleep_duration', {})
        if sleep_trend.get('trend_direction') == 'increasing':
            summary['key_strengths'].append('Improving sleep duration')
        
        # Identify areas for improvement
        heart_trend = trends.get('heart_rate', {})
        if heart_trend.get('trend_direction') == 'increasing':
            summary['areas_for_improvement'].append('Managing heart rate levels')
        
        if steps_trend.get('trend_direction') == 'decreasing':
            summary['areas_for_improvement'].append('Maintaining activity levels')
        
        # Generate recommendations
        if 'Managing heart rate levels' in summary['areas_for_improvement']:
            summary['recommendations'].append('Consider stress management techniques')
        
        if 'Maintaining activity levels' in summary['areas_for_improvement']:
            summary['recommendations'].append('Set small, achievable activity goals')
        
        return summary
    
    def generate_health_alerts(self) -> List[Dict[str, Any]]:
        """Generate health alerts based on recent data"""
        
        alerts = []
        
        # Check for recent anomalies
        recent_anomalies = self._check_recent_anomalies()
        alerts.extend(recent_anomalies)
        
        # Check for inactivity
        inactivity_alerts = self._check_inactivity()
        alerts.extend(inactivity_alerts)
        
        # Check for poor sleep patterns
        sleep_alerts = self._check_sleep_patterns()
        alerts.extend(sleep_alerts)
        
        # Check for elevated heart rate
        heart_rate_alerts = self._check_heart_rate_issues()
        alerts.extend(heart_rate_alerts)
        
        # Save alerts to database
        self._save_alerts_to_database(alerts)
        
        return alerts
    
    def _check_recent_anomalies(self) -> List[Dict[str, Any]]:
        """Check for recent health anomalies"""
        
        alerts = []
        
        # Check heart rate anomalies in last 24 hours
        yesterday = self.now - timedelta(hours=24)
        
        heart_rate_anomalies = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__gte=yesterday,
            is_anomaly=True
        )
        
        for anomaly in heart_rate_anomalies:
            alerts.append({
                'type': anomaly.anomaly_type,
                'severity': 'high' if 'critical' in anomaly.anomaly_type else 'medium',
                'title': 'Heart Rate Anomaly Detected',
                'message': f'Unusual heart rate of {anomaly.bpm} BPM detected at {anomaly.timestamp.strftime("%H:%M")}',
                'metric_value': anomaly.bpm,
                'metric_unit': 'BPM',
                'related_model': 'HeartRateReading',
                'related_id': str(anomaly.id)
            })
        
        return alerts
    
    def _check_inactivity(self) -> List[Dict[str, Any]]:
        """Check for inactivity patterns"""
        
        alerts = []
        
        today = self.now.date()
        yesterday = today - timedelta(days=1)
        
        # Check if no activities today
        today_activities = Activity.objects.filter(
            user=self.user,
            start_time__date=today
        ).count()
        
        if today_activities == 0 and self.now.hour >= 15:  # After 3 PM
            alerts.append({
                'type': 'inactivity',
                'severity': 'low',
                'title': 'Inactive Day',
                'message': 'No physical activities recorded today. Consider adding some movement.',
                'metric_value': 0,
                'metric_unit': 'activities'
            })
        
        # Check for consecutive inactive days
        recent_days = 3
        inactive_days = 0
        
        for i in range(recent_days):
            check_date = today - timedelta(days=i)
            day_activities = Activity.objects.filter(
                user=self.user,
                start_time__date=check_date
            ).count()
            
            if day_activities == 0:
                inactive_days += 1
        
        if inactive_days >= 3:
            alerts.append({
                'type': 'prolonged_inactivity',
                'severity': 'medium',
                'title': 'Multiple Inactive Days',
                'message': f'{inactive_days} consecutive days with no recorded activities.',
                'metric_value': inactive_days,
                'metric_unit': 'days'
            })
        
        return alerts
    
    def _check_sleep_patterns(self) -> List[Dict[str, Any]]:
        """Check for concerning sleep patterns"""
        
        alerts = []
        
        # Check last night's sleep
        yesterday = self.now.date() - timedelta(days=1)
        
        last_sleep = SleepSession.objects.filter(
            user=self.user,
            start_time__date=yesterday
        ).order_by('-start_time').first()
        
        if last_sleep:
            if last_sleep.duration_minutes < 360:  # Less than 6 hours
                alerts.append({
                    'type': 'sleep_poor',
                    'severity': 'medium',
                    'title': 'Short Sleep Duration',
                    'message': f'Only {last_sleep.duration_minutes//60}h {last_sleep.duration_minutes%60}m of sleep last night.',
                    'metric_value': last_sleep.duration_minutes,
                    'metric_unit': 'minutes'
                })
            
            if last_sleep.quality_score and last_sleep.quality_score < 50:
                alerts.append({
                    'type': 'sleep_poor',
                    'severity': 'low',
                    'title': 'Poor Sleep Quality',
                    'message': f'Sleep quality score of {last_sleep.quality_score:.0f}/100 last night.',
                    'metric_value': last_sleep.quality_score,
                    'metric_unit': 'score'
                })
        
        return alerts
    
    def _check_heart_rate_issues(self) -> List[Dict[str, Any]]:
        """Check for heart rate issues"""
        
        alerts = []
        
        # Check recent resting heart rate
        today = self.now.date()
        
        # Get today's heart rate readings
        today_readings = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__date=today,
            context='rest'
        )
        
        if today_readings.exists():
            avg_resting = today_readings.aggregate(avg=Avg('bpm'))['avg']
            
            if avg_resting and avg_resting > 85:
                alerts.append({
                    'type': 'heart_rate_high',
                    'severity': 'medium',
                    'title': 'Elevated Resting Heart Rate',
                    'message': f'Average resting heart rate of {avg_resting:.0f} BPM today.',
                    'metric_value': avg_resting,
                    'metric_unit': 'BPM'
                })
        
        return alerts
    
    def _save_alerts_to_database(self, alerts: List[Dict]):
        """Save generated alerts to database"""
        
        for alert in alerts:
            HealthAlert.objects.create(
                user=self.user,
                alert_type=alert['type'],
                severity=alert['severity'],
                title=alert['title'],
                message=alert['message'],
                metric_value=alert.get('metric_value'),
                metric_unit=alert.get('metric_unit'),
                related_model=alert.get('related_model'),
                related_id=alert.get('related_id')
            )
