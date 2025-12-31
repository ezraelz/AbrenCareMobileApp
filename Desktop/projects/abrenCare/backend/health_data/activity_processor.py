import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from django.db.models import Sum, Avg, Max, Count, Q

from .models import Activity, HeartRateReading, DailySummary

logger = logging.getLogger(__name__)


class ActivityProcessor:
    """Process and analyze activity data"""
    
    @staticmethod
    def analyze_activity(activity: Activity) -> Dict[str, Any]:
        """Analyze a single activity"""
        
        analysis = {
            'intensity_analysis': {},
            'calorie_analysis': {},
            'heart_rate_analysis': {},
            'performance_analysis': {},
            'recovery_analysis': {},
            'recommendations': []
        }
        
        # Analyze intensity
        analysis['intensity_analysis'] = ActivityProcessor._analyze_intensity(activity)
        
        # Analyze calorie burn
        analysis['calorie_analysis'] = ActivityProcessor._analyze_calories(activity)
        
        # Analyze heart rate during activity
        analysis['heart_rate_analysis'] = ActivityProcessor._analyze_heart_rate_during_activity(activity)
        
        # Analyze performance
        analysis['performance_analysis'] = ActivityProcessor._analyze_performance(activity)
        
        # Analyze recovery needs
        analysis['recovery_analysis'] = ActivityProcessor._analyze_recovery(activity)
        
        # Generate recommendations
        analysis['recommendations'] = ActivityProcessor._generate_activity_recommendations(analysis)
        
        return analysis
    
    @staticmethod
    def _analyze_intensity(activity: Activity) -> Dict[str, Any]:
        """Analyze activity intensity"""
        
        # Calculate MET (Metabolic Equivalent of Task) values
        met_values = {
            'walking': 3.5,
            'running': 8.0,
            'cycling': 7.5,
            'swimming': 6.0,
            'hiking': 6.0,
            'yoga': 2.5,
            'strength_training': 6.0,
            'hiit': 8.5,
            'dancing': 5.0,
            'sports': 7.0,
            'workout': 6.5,
            'other': 4.0
        }
        
        base_met = met_values.get(activity.activity_type, 4.0)
        
        # Adjust based on heart rate if available
        intensity_multiplier = 1.0
        if activity.avg_heart_rate:
            if activity.avg_heart_rate > 160:
                intensity_multiplier = 1.3
            elif activity.avg_heart_rate > 140:
                intensity_multiplier = 1.2
            elif activity.avg_heart_rate > 120:
                intensity_multiplier = 1.1
            elif activity.avg_heart_rate < 100:
                intensity_multiplier = 0.9
        
        met = base_met * intensity_multiplier
        
        # Classify intensity
        if met >= 8.0:
            intensity_level = 'vigorous'
            intensity_description = 'Very high intensity activity'
        elif met >= 6.0:
            intensity_level = 'moderate'
            intensity_description = 'Moderate intensity activity'
        elif met >= 3.0:
            intensity_level = 'light'
            intensity_description = 'Light intensity activity'
        else:
            intensity_level = 'very_light'
            intensity_description = 'Very light activity'
        
        # Calculate intensity minutes (for health guidelines)
        # Moderate = MET 3.0-5.9, Vigorous = MET >= 6.0
        if met >= 6.0:
            intensity_minutes = activity.duration_minutes * 2  # Vigorous counts double
            intensity_type = 'vigorous'
        elif met >= 3.0:
            intensity_minutes = activity.duration_minutes
            intensity_type = 'moderate'
        else:
            intensity_minutes = 0
            intensity_type = 'light'
        
        return {
            'met_value': round(met, 1),
            'intensity_level': intensity_level,
            'intensity_description': intensity_description,
            'intensity_minutes': intensity_minutes,
            'intensity_type': intensity_type,
            'base_met': base_met,
            'heart_rate_adjustment': intensity_multiplier
        }
    
    @staticmethod
    def _analyze_calories(activity: Activity) -> Dict[str, Any]:
        """Analyze calorie burn"""
        
        # Calculate calories per minute
        calories_per_minute = activity.calories_per_minute
        
        # Compare with expected values
        expected_ranges = {
            'walking': (4.0, 6.0),
            'running': (10.0, 16.0),
            'cycling': (8.0, 12.0),
            'swimming': (8.0, 14.0),
            'hiking': (6.0, 10.0),
            'yoga': (3.0, 5.0),
            'strength_training': (6.0, 9.0),
            'hiit': (12.0, 18.0),
            'dancing': (5.0, 8.0),
            'sports': (7.0, 12.0),
            'workout': (6.0, 10.0),
            'other': (4.0, 7.0)
        }
        
        expected_min, expected_max = expected_ranges.get(activity.activity_type, (4.0, 7.0))
        
        efficiency = 'optimal'
        if calories_per_minute < expected_min:
            efficiency = 'low'
            message = 'Calorie burn lower than expected for this activity type'
        elif calories_per_minute > expected_max:
            efficiency = 'high'
            message = 'Calorie burn higher than expected for this activity type'
        else:
            message = 'Calorie burn within expected range'
        
        # Calculate percentage of daily calorie needs
        # Average daily calorie needs: 2000 for women, 2500 for men
        daily_calorie_needs = 2250  # Should be user-specific
        percentage_daily = (activity.calories_burned / daily_calorie_needs) * 100
        
        return {
            'calories_burned': round(activity.calories_burned, 1),
            'calories_per_minute': round(calories_per_minute, 2),
            'efficiency': efficiency,
            'message': message,
            'expected_range': f'{expected_min}-{expected_max} cal/min',
            'percentage_daily_needs': round(percentage_daily, 1),
            'activity_duration_minutes': activity.duration_minutes
        }
    
    @staticmethod
    def _analyze_heart_rate_during_activity(activity: Activity) -> Dict[str, Any]:
        """Analyze heart rate during activity"""
        
        if not activity.avg_heart_rate:
            return {'status': 'no_data', 'message': 'No heart rate data available for this activity'}
        
        # Get heart rate zones
        zones = ActivityProcessor._calculate_heart_rate_zones(activity)
        
        # Calculate heart rate reserve (HRR)
        # HRR = (HR during exercise - Resting HR) / (Max HR - Resting HR) * 100
        resting_hr = 65  # Should be user-specific from profile
        max_hr = 180  # Should be user-specific (220 - age)
        
        if activity.avg_heart_rate and resting_hr and max_hr:
            hrr_percentage = ((activity.avg_heart_rate - resting_hr) / (max_hr - resting_hr)) * 100
        else:
            hrr_percentage = None
        
        # Analyze heart rate response
        response = 'normal'
        if activity.max_heart_rate and max_hr:
            if activity.max_heart_rate > max_hr * 0.95:
                response = 'very_high'
                message = 'Heart rate reached near maximum levels'
            elif activity.max_heart_rate > max_hr * 0.85:
                response = 'high'
                message = 'Heart rate reached high intensity levels'
            elif activity.max_heart_rate > max_hr * 0.70:
                response = 'moderate'
                message = 'Heart rate at moderate intensity levels'
            else:
                response = 'low'
                message = 'Heart rate at low intensity levels'
        else:
            message = 'Normal heart rate response'
        
        # Check for heart rate recovery
        recovery_analysis = ActivityProcessor._analyze_heart_rate_recovery(activity)
        
        return {
            'average_bpm': activity.avg_heart_rate,
            'maximum_bpm': activity.max_heart_rate,
            'minimum_bpm': activity.min_heart_rate,
            'heart_rate_zones': zones,
            'heart_rate_reserve_percentage': round(hrr_percentage, 1) if hrr_percentage else None,
            'response_level': response,
            'message': message,
            'recovery_analysis': recovery_analysis
        }
    
    @staticmethod
    def _calculate_heart_rate_zones(activity: Activity) -> Dict[str, Any]:
        """Calculate time spent in heart rate zones"""
        
        if not activity.heart_rate_zones:
            return {'status': 'no_data', 'message': 'No heart rate zone data available'}
        
        return activity.heart_rate_zones
    
    @staticmethod
    def _analyze_heart_rate_recovery(activity: Activity) -> Dict[str, Any]:
        """Analyze heart rate recovery after activity"""
        
        # In production, this would analyze HR readings after activity ends
        # For now, we'll provide a placeholder
        
        return {
            'status': 'analysis_not_available',
            'message': 'Heart rate recovery analysis requires post-activity heart rate data',
            'recommendation': 'Consider tracking heart rate for 5 minutes after exercise'
        }
    
    @staticmethod
    def _analyze_performance(activity: Activity) -> Dict[str, Any]:
        """Analyze activity performance"""
        
        analysis = {
            'pace_analysis': {},
            'distance_analysis': {},
            'efficiency_analysis': {}
        }
        
        # Pace analysis (for running, cycling, walking)
        if activity.distance_km and activity.duration_minutes > 0:
            if not activity.avg_pace_min_per_km:
                pace = activity.duration_minutes / activity.distance_km
            else:
                pace = activity.avg_pace_min_per_km
            
            analysis['pace_analysis'] = {
                'pace_min_per_km': round(pace, 2),
                'speed_kmh': round(60 / pace, 1) if pace > 0 else 0,
                'evaluation': ActivityProcessor._evaluate_pace(activity.activity_type, pace)
            }
        
        # Distance analysis
        if activity.distance_km:
            analysis['distance_analysis'] = {
                'distance_km': round(activity.distance_km, 2),
                'evaluation': ActivityProcessor._evaluate_distance(activity.activity_type, activity.distance_km)
            }
        
        # Efficiency analysis (steps per minute for walking/running)
        if activity.steps and activity.duration_minutes > 0:
            steps_per_minute = activity.steps / activity.duration_minutes
            analysis['efficiency_analysis'] = {
                'steps_per_minute': round(steps_per_minute, 1),
                'cadence': round(steps_per_minute * 2, 1),  # Steps per minute * 2 = cadence (steps per minute per foot)
                'evaluation': ActivityProcessor._evaluate_cadence(steps_per_minute)
            }
        
        return analysis
    
    @staticmethod
    def _evaluate_pace(activity_type: str, pace: float) -> Dict[str, Any]:
        """Evaluate pace for different activity types"""
        
        pace_ranges = {
            'walking': {'fast': (8.0, 10.0), 'moderate': (10.0, 15.0), 'slow': (15.0, 20.0)},
            'running': {'fast': (4.0, 5.0), 'moderate': (5.0, 6.5), 'slow': (6.5, 8.0)},
            'cycling': {'fast': (2.0, 3.0), 'moderate': (3.0, 4.0), 'slow': (4.0, 5.0)}  # min/km
        }
        
        if activity_type not in pace_ranges:
            return {'status': 'not_applicable', 'message': 'Pace evaluation not available for this activity'}
        
        ranges = pace_ranges[activity_type]
        
        if pace <= ranges['fast'][1]:
            return {'status': 'fast', 'message': f'Fast pace for {activity_type}'}
        elif pace <= ranges['moderate'][1]:
            return {'status': 'moderate', 'message': f'Moderate pace for {activity_type}'}
        else:
            return {'status': 'slow', 'message': f'Slow pace for {activity_type}'}
    
    @staticmethod
    def _evaluate_distance(activity_type: str, distance: float) -> Dict[str, Any]:
        """Evaluate distance for different activity types"""
        
        distance_ranges = {
            'walking': {'long': (5.0, float('inf')), 'moderate': (3.0, 5.0), 'short': (0, 3.0)},
            'running': {'long': (10.0, float('inf')), 'moderate': (5.0, 10.0), 'short': (0, 5.0)},
            'cycling': {'long': (30.0, float('inf')), 'moderate': (15.0, 30.0), 'short': (0, 15.0)},
            'swimming': {'long': (1.5, float('inf')), 'moderate': (0.5, 1.5), 'short': (0, 0.5)}
        }
        
        if activity_type not in distance_ranges:
            return {'status': 'not_applicable', 'message': 'Distance evaluation not available for this activity'}
        
        ranges = distance_ranges[activity_type]
        
        if distance >= ranges['long'][0]:
            return {'status': 'long', 'message': f'Long distance for {activity_type}'}
        elif distance >= ranges['moderate'][0]:
            return {'status': 'moderate', 'message': f'Moderate distance for {activity_type}'}
        else:
            return {'status': 'short', 'message': f'Short distance for {activity_type}'}
    
    @staticmethod
    def _evaluate_cadence(steps_per_minute: float) -> Dict[str, Any]:
        """Evaluate walking/running cadence"""
        
        if steps_per_minute >= 120:
            return {'status': 'excellent', 'message': 'Optimal cadence for running efficiency'}
        elif steps_per_minute >= 100:
            return {'status': 'good', 'message': 'Good cadence for running'}
        elif steps_per_minute >= 80:
            return {'status': 'fair', 'message': 'Moderate cadence, could be improved'}
        else:
            return {'status': 'poor', 'message': 'Low cadence, consider increasing step rate'}
    
    @staticmethod
    def _analyze_recovery(activity: Activity) -> Dict[str, Any]:
        """Analyze recovery needs after activity"""
        
        # Calculate training load (TRIMP - Training Impulse)
        # Simplified version: duration * average HR
        if activity.avg_heart_rate and activity.duration_minutes:
            training_load = activity.duration_minutes * activity.avg_heart_rate
        else:
            training_load = activity.duration_minutes * 120  # Estimate
        
        # Estimate recovery time based on training load and intensity
        if training_load < 2000:
            recovery_hours = 12
            recovery_level = 'light'
        elif training_load < 4000:
            recovery_hours = 24
            recovery_level = 'moderate'
        elif training_load < 6000:
            recovery_hours = 36
            recovery_level = 'hard'
        else:
            recovery_hours = 48
            recovery_level = 'very_hard'
        
        # Generate recovery recommendations
        recommendations = []
        if recovery_level in ['hard', 'very_hard']:
            recommendations.append('Consider active recovery (light walking, stretching) tomorrow')
            recommendations.append('Ensure adequate protein intake for muscle repair')
            recommendations.append('Get extra sleep tonight')
        
        if activity.activity_type == 'strength_training':
            recommendations.append('Allow 48 hours before working same muscle groups again')
        
        return {
            'training_load': round(training_load, 1),
            'estimated_recovery_hours': recovery_hours,
            'recovery_level': recovery_level,
            'recovery_recommendations': recommendations,
            'next_workout_timing': f'Consider waiting {recovery_hours} hours before next intense workout'
        }
    
    @staticmethod
    def _generate_activity_recommendations(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate activity recommendations"""
        
        recommendations = []
        
        # Intensity recommendations
        intensity_analysis = analysis.get('intensity_analysis', {})
        if intensity_analysis.get('intensity_level') == 'very_light':
            recommendations.append({
                'category': 'intensity',
                'priority': 'medium',
                'title': 'Increase Activity Intensity',
                'description': 'Consider adding more vigorous activities to your routine.',
                'actions': [
                    'Add intervals to your workouts',
                    'Try new activities that challenge you',
                    'Gradually increase duration and intensity'
                ]
            })
        
        # Calorie efficiency recommendations
        calorie_analysis = analysis.get('calorie_analysis', {})
        if calorie_analysis.get('efficiency') == 'low':
            recommendations.append({
                'category': 'efficiency',
                'priority': 'low',
                'title': 'Improve Exercise Efficiency',
                'description': 'Your calorie burn is lower than expected for this activity type.',
                'actions': [
                    'Focus on proper form and technique',
                    'Increase resistance or incline',
                    'Maintain consistent pace throughout'
                ]
            })
        
        # Recovery recommendations
        recovery_analysis = analysis.get('recovery_analysis', {})
        if recovery_analysis.get('recovery_level') in ['hard', 'very_hard']:
            recommendations.append({
                'category': 'recovery',
                'priority': 'high',
                'title': 'Prioritize Recovery',
                'description': 'This was a demanding workout that requires proper recovery.',
                'actions': [
                    'Stay hydrated and eat nutrient-rich foods',
                    'Consider foam rolling or massage',
                    'Get extra sleep tonight'
                ]
            })
        
        return recommendations
    
    @staticmethod
    def analyze_activity_patterns(user, days: int = 30) -> Dict[str, Any]:
        """Analyze activity patterns over time"""
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get activities in the period
        activities = Activity.objects.filter(
            user=user,
            start_time__date__range=[start_date, end_date]
        ).order_by('start_time')
        
        if not activities.exists():
            return {'status': 'no_data', 'message': f'No activity data for the last {days} days'}
        
        # Calculate statistics
        total_activities = activities.count()
        total_duration = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
        total_calories = activities.aggregate(total=Sum('calories_burned'))['total'] or 0
        total_steps = activities.aggregate(total=Sum('steps'))['total'] or 0
        
        # Analyze by activity type
        by_type = activities.values('activity_type').annotate(
            count=Count('id'),
            total_duration=Sum('duration_minutes'),
            total_calories=Sum('calories_burned'),
            avg_duration=Avg('duration_minutes')
        ).order_by('-count')
        
        # Analyze intensity distribution
        intensity_distribution = activities.values('intensity').annotate(
            count=Count('id'),
            total_duration=Sum('duration_minutes')
        )
        
        # Calculate weekly patterns
        weekly_patterns = ActivityProcessor._analyze_weekly_patterns(activities)
        
        # Calculate progress over time
        progress = ActivityProcessor._calculate_progress(activities, days)
        
        # Check against health guidelines
        guideline_check = ActivityProcessor._check_health_guidelines(activities, days)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'overview': {
                'total_activities': total_activities,
                'total_duration_hours': round(total_duration / 60, 1),
                'total_calories': round(total_calories, 1),
                'total_steps': total_steps,
                'average_daily_minutes': round(total_duration / days, 1),
                'average_daily_calories': round(total_calories / days, 1)
            },
            'by_activity_type': list(by_type),
            'intensity_distribution': list(intensity_distribution),
            'weekly_patterns': weekly_patterns,
            'progress_analysis': progress,
            'guideline_check': guideline_check,
            'recommendations': ActivityProcessor._generate_pattern_recommendations(
                total_duration, by_type, guideline_check
            )
        }
    
    @staticmethod
    def _analyze_weekly_patterns(activities) -> Dict[str, Any]:
        """Analyze activity patterns by day of week"""
        
        patterns = {}
        
        # Group by day of week
        for activity in activities:
            weekday = activity.start_time.strftime('%A')
            if weekday not in patterns:
                patterns[weekday] = {
                    'count': 0,
                    'total_duration': 0,
                    'total_calories': 0
                }
            
            patterns[weekday]['count'] += 1
            patterns[weekday]['total_duration'] += activity.duration_minutes
            patterns[weekday]['total_calories'] += activity.calories_burned
        
        # Find most and least active days
        if patterns:
            most_active = max(patterns.items(), key=lambda x: x[1]['total_duration'])
            least_active = min(patterns.items(), key=lambda x: x[1]['total_duration'])
        else:
            most_active = least_active = (None, {})
        
        return {
            'daily_patterns': patterns,
            'most_active_day': {
                'day': most_active[0],
                'duration_minutes': most_active[1].get('total_duration', 0)
            },
            'least_active_day': {
                'day': least_active[0],
                'duration_minutes': least_active[1].get('total_duration', 0)
            }
        }
    
    @staticmethod
    def _calculate_progress(activities, days: int) -> Dict[str, Any]:
        """Calculate progress over time"""
        
        if len(activities) < 2:
            return {'status': 'insufficient_data', 'message': 'Need more data to calculate progress'}
        
        # Split into two halves for comparison
        midpoint = len(activities) // 2
        first_half = activities[:midpoint]
        second_half = activities[midpoint:]
        
        # Calculate averages for each half
        def calculate_averages(activity_list):
            if not activity_list:
                return {}
            
            total_duration = sum(a.duration_minutes for a in activity_list)
            total_calories = sum(a.calories_burned for a in activity_list)
            
            return {
                'avg_duration': total_duration / len(activity_list),
                'avg_calories': total_calories / len(activity_list),
                'frequency': len(activity_list) / (days / 2)  # Activities per day
            }
        
        first_avg = calculate_averages(first_half)
        second_avg = calculate_averages(second_half)
        
        # Calculate changes
        changes = {}
        for metric in ['avg_duration', 'avg_calories', 'frequency']:
            if metric in first_avg and metric in second_avg and first_avg[metric] > 0:
                change = ((second_avg[metric] - first_avg[metric]) / first_avg[metric]) * 100
                changes[metric] = round(change, 1)
        
        return {
            'first_half': first_avg,
            'second_half': second_avg,
            'changes': changes,
            'trend': 'improving' if changes.get('frequency', 0) > 0 else 'declining' if changes.get('frequency', 0) < 0 else 'stable'
        }
    
    @staticmethod
    def _check_health_guidelines(activities, days: int) -> Dict[str, Any]:
        """Check against health activity guidelines"""
        
        # WHO guidelines: 150-300 minutes moderate or 75-150 minutes vigorous per week
        # Calculate weekly averages
        
        total_moderate_minutes = sum(
            a.duration_minutes for a in activities 
            if a.intensity in ['moderate', 'vigorous', 'maximal']
        )
        
        weekly_average = (total_moderate_minutes / days) * 7
        
        guidelines = {
            'minimum_weekly': 150,
            'target_weekly': 300,
            'vigorous_equivalent': 75  # 1 minute vigorous = 2 minutes moderate
        }
        
        status = 'meeting_target'
        if weekly_average >= guidelines['target_weekly']:
            message = 'Exceeding weekly activity targets'
        elif weekly_average >= guidelines['minimum_weekly']:
            status = 'meeting_minimum'
            message = 'Meeting minimum weekly activity guidelines'
        else:
            status = 'below_minimum'
            message = 'Below minimum weekly activity guidelines'
        
        return {
            'weekly_average_minutes': round(weekly_average, 1),
            'status': status,
            'message': message,
            'guidelines': guidelines,
            'percentage_of_target': min(100, (weekly_average / guidelines['target_weekly']) * 100)
        }
    
    @staticmethod
    def _generate_pattern_recommendations(
        total_duration: float, 
        by_type: List[Dict], 
        guideline_check: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on activity patterns"""
        
        recommendations = []
        
        # Guideline-based recommendations
        if guideline_check.get('status') == 'below_minimum':
            needed_minutes = guideline_check['guidelines']['minimum_weekly'] - guideline_check['weekly_average_minutes']
            recommendations.append(
                f"Aim to add {round(needed_minutes/7, 1)} minutes of activity per day to meet minimum guidelines."
            )
        
        # Variety recommendations
        if len(by_type) < 3:
            recommendations.append("Consider adding more variety to your activities for balanced fitness.")
        
        # Duration recommendations
        daily_average = total_duration / 30  # Assuming 30 days
        if daily_average < 30:
            recommendations.append("Try to increase your daily activity time to at least 30 minutes.")
        
        # Strength training recommendation
        has_strength = any(item['activity_type'] == 'strength_training' for item in by_type)
        if not has_strength:
            recommendations.append("Consider adding strength training 2-3 times per week for muscle health.")
        
        return recommendations
    