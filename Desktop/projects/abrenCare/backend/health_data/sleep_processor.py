import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.db.models import Avg, Count, Q

from .models import SleepSession, HeartRateReading

logger = logging.getLogger(__name__)


class SleepProcessor:
    """Process and analyze sleep data"""
    
    @staticmethod
    def analyze_sleep_session(sleep_session: SleepSession) -> Dict[str, Any]:
        """Analyze a single sleep session"""
        
        analysis = {
            'overall_score': sleep_session.quality_score or SleepProcessor._calculate_sleep_score(sleep_session),
            'stage_analysis': {},
            'efficiency_analysis': {},
            'consistency_analysis': {},
            'recommendations': []
        }
        
        # Analyze sleep stages
        analysis['stage_analysis'] = SleepProcessor._analyze_sleep_stages(sleep_session)
        
        # Analyze sleep efficiency
        analysis['efficiency_analysis'] = SleepProcessor._analyze_sleep_efficiency(sleep_session)
        
        # Get heart rate during sleep
        heart_rate_analysis = SleepProcessor._analyze_heart_rate_during_sleep(sleep_session)
        analysis['heart_rate_analysis'] = heart_rate_analysis
        
        # Generate recommendations
        analysis['recommendations'] = SleepProcessor._generate_sleep_recommendations(
            analysis['stage_analysis'],
            analysis['efficiency_analysis'],
            heart_rate_analysis
        )
        
        # Detect sleep issues
        analysis['issues'] = SleepProcessor._detect_sleep_issues(sleep_session, analysis)
        
        return analysis
    
    @staticmethod
    def _calculate_sleep_score(sleep_session: SleepSession) -> float:
        """Calculate sleep quality score based on multiple factors"""
        
        weights = {
            'duration': 0.30,
            'efficiency': 0.25,
            'deep_sleep': 0.20,
            'rem_sleep': 0.15,
            'interruptions': 0.10
        }
        
        scores = {}
        
        # Duration score (optimal: 7-9 hours)
        sleep_hours = sleep_session.duration_minutes / 60
        if 7 <= sleep_hours <= 9:
            scores['duration'] = 100
        elif 6 <= sleep_hours < 7 or 9 < sleep_hours <= 10:
            scores['duration'] = 70
        elif 5 <= sleep_hours < 6 or 10 < sleep_hours <= 11:
            scores['duration'] = 40
        else:
            scores['duration'] = 20
        
        # Efficiency score (optimal: >85%)
        efficiency = sleep_session.sleep_efficiency or (
            (sleep_session.total_sleep_minutes / sleep_session.duration_minutes * 100)
            if sleep_session.duration_minutes > 0 else 0
        )
        if efficiency >= 90:
            scores['efficiency'] = 100
        elif efficiency >= 85:
            scores['efficiency'] = 85
        elif efficiency >= 75:
            scores['efficiency'] = 60
        else:
            scores['efficiency'] = 30
        
        # Deep sleep score (optimal: 15-25% of total sleep)
        deep_sleep_percentage = sleep_session.deep_sleep_percentage
        if 15 <= deep_sleep_percentage <= 25:
            scores['deep_sleep'] = 100
        elif 10 <= deep_sleep_percentage < 15 or 25 < deep_sleep_percentage <= 30:
            scores['deep_sleep'] = 70
        elif 5 <= deep_sleep_percentage < 10 or 30 < deep_sleep_percentage <= 35:
            scores['deep_sleep'] = 40
        else:
            scores['deep_sleep'] = 20
        
        # REM sleep score (optimal: 20-25% of total sleep)
        rem_sleep_percentage = sleep_session.rem_sleep_percentage
        if 20 <= rem_sleep_percentage <= 25:
            scores['rem_sleep'] = 100
        elif 15 <= rem_sleep_percentage < 20 or 25 < rem_sleep_percentage <= 30:
            scores['rem_sleep'] = 70
        elif 10 <= rem_sleep_percentage < 15 or 30 < rem_sleep_percentage <= 35:
            scores['rem_sleep'] = 40
        else:
            scores['rem_sleep'] = 20
        
        # Interruption score (optimal: <3 interruptions)
        interruptions = sleep_session.interruptions
        if interruptions <= 2:
            scores['interruptions'] = 100
        elif interruptions <= 5:
            scores['interruptions'] = 70
        elif interruptions <= 10:
            scores['interruptions'] = 40
        else:
            scores['interruptions'] = 10
        
        # Calculate weighted score
        total_score = sum(scores[factor] * weight for factor, weight in weights.items())
        
        return round(total_score, 1)
    
    @staticmethod
    def _analyze_sleep_stages(sleep_session: SleepSession) -> Dict[str, Any]:
        """Analyze sleep stage distribution"""
        
        total_sleep = sleep_session.total_sleep_minutes
        
        if total_sleep == 0:
            return {
                'status': 'no_sleep_data',
                'recommendations': ['Ensure sleep tracking is enabled on your device.']
            }
        
        # Calculate percentages
        stage_percentages = {
            'awake': (sleep_session.awake_minutes / sleep_session.duration_minutes * 100) if sleep_session.duration_minutes > 0 else 0,
            'light': (sleep_session.light_minutes / total_sleep * 100) if total_sleep > 0 else 0,
            'deep': (sleep_session.deep_sleep_percentage),
            'rem': (sleep_session.rem_sleep_percentage)
        }
        
        # Evaluate each stage
        stage_evaluations = {}
        
        # Awake time evaluation
        awake_percentage = stage_percentages['awake']
        if awake_percentage <= 5:
            stage_evaluations['awake'] = {'status': 'excellent', 'message': 'Minimal awake time during sleep'}
        elif awake_percentage <= 10:
            stage_evaluations['awake'] = {'status': 'good', 'message': 'Normal awake time'}
        elif awake_percentage <= 20:
            stage_evaluations['awake'] = {'status': 'fair', 'message': 'Slightly elevated awake time'}
        else:
            stage_evaluations['awake'] = {'status': 'poor', 'message': 'High awake time during sleep'}
        
        # Deep sleep evaluation
        deep_percentage = stage_percentages['deep']
        if 15 <= deep_percentage <= 25:
            stage_evaluations['deep'] = {'status': 'excellent', 'message': 'Optimal deep sleep'}
        elif 10 <= deep_percentage < 15 or 25 < deep_percentage <= 30:
            stage_evaluations['deep'] = {'status': 'good', 'message': 'Adequate deep sleep'}
        elif 5 <= deep_percentage < 10 or 30 < deep_percentage <= 35:
            stage_evaluations['deep'] = {'status': 'fair', 'message': 'Moderate deep sleep'}
        else:
            stage_evaluations['deep'] = {'status': 'poor', 'message': 'Insufficient deep sleep'}
        
        # REM sleep evaluation
        rem_percentage = stage_percentages['rem']
        if 20 <= rem_percentage <= 25:
            stage_evaluations['rem'] = {'status': 'excellent', 'message': 'Optimal REM sleep'}
        elif 15 <= rem_percentage < 20 or 25 < rem_percentage <= 30:
            stage_evaluations['rem'] = {'status': 'good', 'message': 'Adequate REM sleep'}
        elif 10 <= rem_percentage < 15 or 30 < rem_percentage <= 35:
            stage_evaluations['rem'] = {'status': 'fair', 'message': 'Moderate REM sleep'}
        else:
            stage_evaluations['rem'] = {'status': 'poor', 'message': 'Insufficient REM sleep'}
        
        return {
            'percentages': {k: round(v, 1) for k, v in stage_percentages.items()},
            'evaluations': stage_evaluations,
            'total_sleep_minutes': total_sleep,
            'duration_minutes': sleep_session.duration_minutes
        }
    
    @staticmethod
    def _analyze_sleep_efficiency(sleep_session: SleepSession) -> Dict[str, Any]:
        """Analyze sleep efficiency"""
        
        efficiency = sleep_session.sleep_efficiency or (
            (sleep_session.total_sleep_minutes / sleep_session.duration_minutes * 100)
            if sleep_session.duration_minutes > 0 else 0
        )
        
        if efficiency >= 90:
            status = 'excellent'
            message = 'Very efficient sleep'
        elif efficiency >= 85:
            status = 'good'
            message = 'Efficient sleep'
        elif efficiency >= 75:
            status = 'fair'
            message = 'Moderate sleep efficiency'
        else:
            status = 'poor'
            message = 'Low sleep efficiency - consider improving sleep habits'
        
        return {
            'efficiency_percentage': round(efficiency, 1),
            'status': status,
            'message': message,
            'time_in_bed_minutes': sleep_session.duration_minutes,
            'actual_sleep_minutes': sleep_session.total_sleep_minutes
        }
    
    @staticmethod
    def _analyze_heart_rate_during_sleep(sleep_session: SleepSession) -> Dict[str, Any]:
        """Analyze heart rate during sleep"""
        
        try:
            # Get heart rate readings during sleep
            heart_rate_readings = HeartRateReading.objects.filter(
                user=sleep_session.user,
                timestamp__range=[sleep_session.start_time, sleep_session.end_time],
                context='sleep'
            ).order_by('timestamp')
            
            if not heart_rate_readings.exists():
                return {'status': 'no_data', 'message': 'No heart rate data during sleep'}
            
            bpm_values = [hr.bpm for hr in heart_rate_readings]
            
            # Calculate statistics
            avg_hr = np.mean(bpm_values)
            min_hr = min(bpm_values)
            max_hr = max(bpm_values)
            hr_std = np.std(bpm_values)
            
            # Evaluate resting heart rate during sleep
            # Typically, sleeping HR should be 10-20% lower than daytime resting HR
            resting_hr_status = 'normal'
            if avg_hr > 70:
                resting_hr_status = 'elevated'
                message = 'Elevated heart rate during sleep may indicate stress or poor recovery'
            elif avg_hr < 40:
                resting_hr_status = 'low'
                message = 'Very low heart rate during sleep'
            else:
                message = 'Normal heart rate during sleep'
            
            # Check for heart rate variability
            hrv_status = 'normal'
            if hr_std < 5:
                hrv_status = 'low_variability'
                message += '. Low heart rate variability detected.'
            elif hr_std > 15:
                hrv_status = 'high_variability'
                message += '. High heart rate variability detected.'
            
            return {
                'average_bpm': round(avg_hr, 1),
                'minimum_bpm': min_hr,
                'maximum_bpm': max_hr,
                'variability_std': round(hr_std, 2),
                'readings_count': len(bpm_values),
                'resting_hr_status': resting_hr_status,
                'hrv_status': hrv_status,
                'message': message,
                'optimal_range': '40-70 BPM'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing heart rate during sleep: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def _detect_sleep_issues(sleep_session: SleepSession, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential sleep issues"""
        
        issues = []
        
        # Check for insomnia patterns
        if sleep_session.awake_minutes > 60 or sleep_session.interruptions > 10:
            issues.append({
                'type': 'potential_insomnia',
                'severity': 'medium',
                'description': 'Extended awake time or frequent interruptions',
                'suggestions': [
                    'Establish a consistent sleep schedule',
                    'Avoid screens 1 hour before bed',
                    'Create a relaxing bedtime routine'
                ]
            })
        
        # Check for insufficient deep sleep
        stage_analysis = analysis.get('stage_analysis', {})
        if 'evaluations' in stage_analysis:
            deep_eval = stage_analysis['evaluations'].get('deep', {})
            if deep_eval.get('status') == 'poor':
                issues.append({
                    'type': 'insufficient_deep_sleep',
                    'severity': 'medium',
                    'description': 'Deep sleep is below optimal levels',
                    'suggestions': [
                        'Avoid caffeine after 2 PM',
                        'Ensure complete darkness in bedroom',
                        'Maintain cool room temperature (18-20°C)'
                    ]
                })
        
        # Check for sleep efficiency issues
        efficiency_analysis = analysis.get('efficiency_analysis', {})
        if efficiency_analysis.get('status') == 'poor':
            issues.append({
                'type': 'low_sleep_efficiency',
                'severity': 'low',
                'description': 'Spending too much time in bed awake',
                'suggestions': [
                    'Only go to bed when sleepy',
                    'Get out of bed if awake for more than 20 minutes',
                    'Use bed only for sleep and intimacy'
                ]
            })
        
        # Check for restless sleep
        if sleep_session.was_restless:
            issues.append({
                'type': 'restless_sleep',
                'severity': 'low',
                'description': 'Restless sleep detected',
                'suggestions': [
                    'Practice relaxation techniques before bed',
                    'Consider magnesium supplements',
                    'Ensure comfortable bedding'
                ]
            })
        
        return issues
    
    @staticmethod
    def _generate_sleep_recommendations(
        stage_analysis: Dict[str, Any],
        efficiency_analysis: Dict[str, Any],
        heart_rate_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate personalized sleep recommendations"""
        
        recommendations = []
        
        # Stage-based recommendations
        if 'evaluations' in stage_analysis:
            evaluations = stage_analysis['evaluations']
            
            # Deep sleep recommendations
            if evaluations.get('deep', {}).get('status') in ['fair', 'poor']:
                recommendations.append({
                    'category': 'deep_sleep',
                    'priority': 'medium',
                    'title': 'Improve Deep Sleep',
                    'description': 'Deep sleep is crucial for physical recovery and memory consolidation.',
                    'actions': [
                        'Exercise regularly but finish at least 3 hours before bedtime',
                        'Limit alcohol consumption, especially close to bedtime',
                        'Maintain a consistent sleep schedule'
                    ]
                })
            
            # REM sleep recommendations
            if evaluations.get('rem', {}).get('status') in ['fair', 'poor']:
                recommendations.append({
                    'category': 'rem_sleep',
                    'priority': 'medium',
                    'title': 'Enhance REM Sleep',
                    'description': 'REM sleep is important for emotional processing and memory.',
                    'actions': [
                        'Reduce stress through meditation or journaling',
                        'Ensure adequate total sleep time (7-9 hours)',
                        'Avoid sleeping pills that can suppress REM sleep'
                    ]
                })
        
        # Efficiency-based recommendations
        if efficiency_analysis.get('status') in ['fair', 'poor']:
            recommendations.append({
                'category': 'efficiency',
                'priority': 'high',
                'title': 'Increase Sleep Efficiency',
                'description': 'Improve the percentage of time in bed actually spent sleeping.',
                'actions': [
                    'Establish a relaxing pre-sleep routine',
                    'Keep your bedroom dark, quiet, and cool',
                    'Avoid naps longer than 30 minutes during the day'
                ]
            })
        
        # Heart rate-based recommendations
        if heart_rate_analysis.get('resting_hr_status') == 'elevated':
            recommendations.append({
                'category': 'heart_rate',
                'priority': 'medium',
                'title': 'Lower Resting Heart Rate During Sleep',
                'description': 'Elevated heart rate during sleep may indicate stress or poor recovery.',
                'actions': [
                    'Practice deep breathing exercises before bed',
                    'Avoid heavy meals close to bedtime',
                    'Consider tracking stress levels and addressing stressors'
                ]
            })
        
        return recommendations
    
    @staticmethod
    def analyze_sleep_patterns(user, days: int = 14) -> Dict[str, Any]:
        """Analyze sleep patterns over multiple days"""
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get sleep sessions in the period
        sleep_sessions = SleepSession.objects.filter(
            user=user,
            start_time__date__range=[start_date, end_date]
        ).order_by('start_time')
        
        if not sleep_sessions.exists():
            return {'status': 'no_data', 'message': f'No sleep data for the last {days} days'}
        
        # Calculate statistics
        total_sessions = sleep_sessions.count()
        avg_duration = sleep_sessions.aggregate(avg=Avg('duration_minutes'))['avg'] or 0
        avg_efficiency = sleep_sessions.aggregate(avg=Avg('sleep_efficiency'))['avg'] or 0
        avg_score = sleep_sessions.aggregate(avg=Avg('quality_score'))['avg'] or 0
        
        # Analyze consistency
        durations = [s.duration_minutes for s in sleep_sessions]
        duration_std = np.std(durations) if len(durations) > 1 else 0
        
        # Bedtime consistency
        bedtimes = [s.start_time.time() for s in sleep_sessions]
        bedtime_variation = SleepProcessor._calculate_time_variation(bedtimes)
        
        # Wake time consistency
        waketimes = [s.end_time.time() for s in sleep_sessions]
        waketime_variation = SleepProcessor._calculate_time_variation(waketimes)
        
        # Sleep debt calculation
        optimal_hours = 7.5  # Optimal sleep per night in hours
        sleep_debt = sum(max(0, optimal_hours - (s.duration_minutes / 60)) for s in sleep_sessions)
        
        # Identify patterns
        patterns = SleepProcessor._identify_sleep_patterns(sleep_sessions)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'overview': {
                'total_nights': total_sessions,
                'average_duration_hours': round(avg_duration / 60, 1),
                'average_efficiency': round(avg_efficiency, 1),
                'average_score': round(avg_score, 1),
                'sleep_debt_hours': round(sleep_debt, 1)
            },
            'consistency': {
                'duration_consistency': 'high' if duration_std < 60 else 'medium' if duration_std < 120 else 'low',
                'duration_std_minutes': round(duration_std, 1),
                'bedtime_consistency': 'high' if bedtime_variation < 60 else 'medium' if bedtime_variation < 120 else 'low',
                'bedtime_variation_minutes': bedtime_variation,
                'waketime_consistency': 'high' if waketime_variation < 60 else 'medium' if waketime_variation < 120 else 'low',
                'waketime_variation_minutes': waketime_variation
            },
            'patterns': patterns,
            'recommendations': SleepProcessor._generate_pattern_recommendations(
                avg_duration, avg_efficiency, duration_std, bedtime_variation
            )
        }
    
    @staticmethod
    def _calculate_time_variation(times: List) -> float:
        """Calculate variation in times (in minutes)"""
        if len(times) < 2:
            return 0
        
        # Convert times to minutes since midnight
        minutes_list = []
        for t in times:
            minutes = t.hour * 60 + t.minute
            minutes_list.append(minutes)
        
        # Calculate standard deviation
        return np.std(minutes_list)
    
    @staticmethod
    def _identify_sleep_patterns(sleep_sessions) -> List[Dict[str, Any]]:
        """Identify common sleep patterns"""
        
        patterns = []
        
        # Check for weekend oversleep
        weekday_sleep = []
        weekend_sleep = []
        
        for session in sleep_sessions:
            weekday = session.start_time.weekday()  # Monday=0, Sunday=6
            if weekday < 5:  # Monday-Friday
                weekday_sleep.append(session.duration_minutes)
            else:  # Saturday-Sunday
                weekend_sleep.append(session.duration_minutes)
        
        if weekday_sleep and weekend_sleep:
            avg_weekday = np.mean(weekday_sleep)
            avg_weekend = np.mean(weekend_sleep)
            
            if avg_weekend - avg_weekday > 60:  # More than 1 hour difference
                patterns.append({
                    'type': 'weekend_catchup',
                    'description': 'Sleeping significantly longer on weekends',
                    'interpretation': 'May indicate sleep deprivation during weekdays',
                    'difference_minutes': round(avg_weekend - avg_weekday)
                })
        
        # Check for late bedtimes
        late_nights = sum(1 for s in sleep_sessions if s.start_time.hour >= 23)
        if late_nights / len(sleep_sessions) > 0.5:
            patterns.append({
                'type': 'late_bedtimes',
                'description': 'Consistently going to bed after 11 PM',
                'interpretation': 'May affect sleep quality and circadian rhythm'
            })
        
        return patterns
    
    @staticmethod
    def _generate_pattern_recommendations(
        avg_duration: float, 
        avg_efficiency: float, 
        duration_std: float, 
        bedtime_variation: float
    ) -> List[str]:
        """Generate recommendations based on sleep patterns"""
        
        recommendations = []
        
        # Duration recommendations
        if avg_duration < 420:  # Less than 7 hours
            recommendations.append("Aim for 7-9 hours of sleep per night for optimal health.")
        elif avg_duration > 540:  # More than 9 hours
            recommendations.append("Consider if excessive sleep is needed or if there's an underlying health issue.")
        
        # Efficiency recommendations
        if avg_efficiency < 85:
            recommendations.append("Improve sleep efficiency by creating a better sleep environment and routine.")
        
        # Consistency recommendations
        if duration_std > 120:
            recommendations.append("Try to maintain more consistent sleep duration each night.")
        
        if bedtime_variation > 120:
            recommendations.append("Establish a consistent bedtime, even on weekends.")
        
        return recommendations
    