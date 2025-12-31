import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .models import HeartRateReading, SleepSession, Activity

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalies in health data using machine learning"""
    
    def __init__(self, user):
        self.user = user
        self.now = timezone.now()
    
    def detect_heart_rate_anomalies(
        self, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None,
        contamination: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in heart rate data using Isolation Forest"""
        
        if not start_time:
            start_time = self.now - timedelta(days=7)
        if not end_time:
            end_time = self.now
        
        # Get heart rate readings
        readings = HeartRateReading.objects.filter(
            user=self.user,
            timestamp__range=[start_time, end_time]
        ).order_by('timestamp')
        
        if len(readings) < 50:  # Need enough data for anomaly detection
            logger.info(f"Insufficient data for anomaly detection: {len(readings)} readings")
            return []
        
        # Prepare features for anomaly detection
        features = self._extract_heart_rate_features(readings)
        
        if len(features) < 50:
            return []
        
        # Normalize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Train Isolation Forest
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        # Fit and predict
        anomaly_predictions = iso_forest.fit_predict(features_scaled)
        
        # Extract anomalies
        anomalies = []
        for i, (reading, prediction) in enumerate(zip(readings, anomaly_predictions)):
            if prediction == -1:  # -1 indicates anomaly
                anomaly_score = iso_forest.score_samples([features_scaled[i]])[0]
                
                anomalies.append({
                    'reading_id': str(reading.id),
                    'timestamp': reading.timestamp,
                    'bpm': reading.bpm,
                    'context': reading.context,
                    'anomaly_score': float(anomaly_score),
                    'features': features[i].tolist() if hasattr(features[i], 'tolist') else features[i],
                    'detection_method': 'isolation_forest'
                })
        
        # Update database with anomaly flags
        self._update_heart_rate_anomalies(anomalies)
        
        # Group similar anomalies
        grouped_anomalies = self._group_anomalies(anomalies)
        
        return grouped_anomalies
    
    def _extract_heart_rate_features(self, readings) -> np.ndarray:
        """Extract features from heart rate readings for anomaly detection"""
        
        features = []
        
        for i, reading in enumerate(readings):
            # Basic features
            feature_vector = [
                reading.bpm,
                reading.confidence or 1.0,
                self._context_to_numeric(reading.context),
                reading.timestamp.hour,  # Time of day
                reading.timestamp.weekday()  # Day of week
            ]
            
            # Add rolling statistics for context
            if i >= 10:  # Need at least 10 previous readings
                prev_readings = readings[max(0, i-10):i]
                prev_bpm = [r.bpm for r in prev_readings]
                
                feature_vector.extend([
                    np.mean(prev_bpm),
                    np.std(prev_bpm),
                    np.max(prev_bpm),
                    np.min(prev_bpm),
                    (reading.bpm - np.mean(prev_bpm)) / (np.std(prev_bpm) + 1e-6)  # Z-score
                ])
            else:
                feature_vector.extend([reading.bpm, 0, reading.bpm, reading.bpm, 0])
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def _context_to_numeric(self, context: str) -> int:
        """Convert context to numeric value"""
        context_map = {
            'rest': 0,
            'active': 1,
            'workout': 2,
            'recovery': 3,
            'sleep': 4,
            'unknown': 5
        }
        return context_map.get(context, 5)
    
    def _update_heart_rate_anomalies(self, anomalies: List[Dict[str, Any]]):
        """Update heart rate readings with anomaly flags"""
        
        for anomaly in anomalies:
            try:
                reading = HeartRateReading.objects.get(id=anomaly['reading_id'])
                reading.is_anomaly = True
                reading.anomaly_type = 'ml_detected'
                reading.save()
            except HeartRateReading.DoesNotExist:
                continue
    
    def _group_anomalies(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group similar anomalies together"""
        
        if not anomalies:
            return []
        
        # Sort by timestamp
        anomalies.sort(key=lambda x: x['timestamp'])
        
        grouped = []
        current_group = []
        group_threshold = timedelta(minutes=30)  # Group anomalies within 30 minutes
        
        for anomaly in anomalies:
            if not current_group:
                current_group.append(anomaly)
            else:
                last_anomaly = current_group[-1]
                time_diff = anomaly['timestamp'] - last_anomaly['timestamp']
                
                if time_diff <= group_threshold:
                    current_group.append(anomaly)
                else:
                    # Finalize current group
                    grouped.append(self._create_anomaly_group(current_group))
                    current_group = [anomaly]
        
        # Add last group
        if current_group:
            grouped.append(self._create_anomaly_group(current_group))
        
        return grouped
    
    def _create_anomaly_group(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a group from individual anomalies"""
        
        if not anomalies:
            return {}
        
        timestamps = [a['timestamp'] for a in anomalies]
        bpm_values = [a['bpm'] for a in anomalies]
        anomaly_scores = [a['anomaly_score'] for a in anomalies]
        
        # Determine group type based on heart rate values
        avg_bpm = np.mean(bpm_values)
        if avg_bpm > 120:
            group_type = 'sustained_high_heart_rate'
            severity = 'high'
        elif avg_bpm < 50:
            group_type = 'sustained_low_heart_rate'
            severity = 'medium'
        else:
            group_type = 'irregular_heart_rate_pattern'
            severity = 'low'
        
        return {
            'group_type': group_type,
            'severity': severity,
            'start_time': min(timestamps),
            'end_time': max(timestamps),
            'duration_minutes': (max(timestamps) - min(timestamps)).total_seconds() / 60,
            'average_bpm': round(avg_bpm, 1),
            'min_bpm': min(bpm_values),
            'max_bpm': max(bpm_values),
            'average_anomaly_score': round(np.mean(anomaly_scores), 3),
            'anomaly_count': len(anomalies),
            'individual_anomalies': anomalies[:5]  # Include first few for detail
        }
    
    def detect_sleep_anomalies(self, days: int = 30) -> List[Dict[str, Any]]:
        """Detect anomalies in sleep patterns"""
        
        end_date = self.now.date()
        start_date = end_date - timedelta(days=days)
        
        sleep_sessions = SleepSession.objects.filter(
            user=self.user,
            start_time__date__range=[start_date, end_date]
        ).order_by('start_time')
        
        if len(sleep_sessions) < 10:
            return []
        
        # Extract sleep features
        features = []
        sessions_list = []
        
        for session in sleep_sessions:
            feature_vector = [
                session.duration_minutes,
                session.sleep_efficiency or 0,
                session.quality_score or 0,
                session.deep_minutes,
                session.rem_minutes,
                session.awake_minutes,
                session.interruptions,
                session.start_time.weekday()
            ]
            
            features.append(feature_vector)
            sessions_list.append(session)
        
        features_array = np.array(features)
        
        # Normalize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features_array)
        
        # Detect anomalies
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        anomaly_predictions = iso_forest.fit_predict(features_scaled)
        
        # Extract anomalies
        anomalies = []
        for i, (session, prediction) in enumerate(zip(sessions_list, anomaly_predictions)):
            if prediction == -1:
                anomaly_score = iso_forest.score_samples([features_scaled[i]])[0]
                
                # Determine anomaly type
                if session.duration_minutes < 300:  # Less than 5 hours
                    anomaly_type = 'extremely_short_sleep'
                    severity = 'high'
                elif session.duration_minutes > 600:  # More than 10 hours
                    anomaly_type = 'extremely_long_sleep'
                    severity = 'medium'
                elif session.sleep_efficiency and session.sleep_efficiency < 70:
                    anomaly_type = 'very_low_sleep_efficiency'
                    severity = 'medium'
                else:
                    anomaly_type = 'irregular_sleep_pattern'
                    severity = 'low'
                
                anomalies.append({
                    'session_id': str(session.id),
                    'date': session.start_time.date(),
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'duration_minutes': session.duration_minutes,
                    'sleep_efficiency': session.sleep_efficiency,
                    'quality_score': session.quality_score,
                    'anomaly_score': float(anomaly_score)
                })
        
        return anomalies
    
    def detect_activity_anomalies(self, days: int = 30) -> List[Dict[str, Any]]:
        """Detect anomalies in activity patterns"""
        
        end_date = self.now.date()
        start_date = end_date - timedelta(days=days)
        
        activities = Activity.objects.filter(
            user=self.user,
            start_time__date__range=[start_date, end_date]
        ).order_by('start_time')
        
        if len(activities) < 10:
            return []
        
        # Group activities by type
        activities_by_type = {}
        for activity in activities:
            if activity.activity_type not in activities_by_type:
                activities_by_type[activity.activity_type] = []
            activities_by_type[activity.activity_type].append(activity)
        
        anomalies = []
        
        # Detect anomalies for each activity type
        for activity_type, type_activities in activities_by_type.items():
            if len(type_activities) < 5:
                continue
            
            # Extract features for this activity type
            features = []
            activities_list = []
            
            for activity in type_activities:
                feature_vector = [
                    activity.duration_minutes,
                    activity.calories_burned,
                    activity.distance_km or 0,
                    activity.steps or 0,
                    activity.avg_heart_rate or 0,
                    activity.start_time.weekday()
                ]
                
                features.append(feature_vector)
                activities_list.append(activity)
            
            features_array = np.array(features)
            
            # Remove features with no variance
            if features_array.shape[1] > 0 and np.std(features_array, axis=0).sum() > 0:
                # Normalize features
                scaler = StandardScaler()
                features_scaled = scaler.fit_transform(features_array)
                
                # Detect anomalies
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                anomaly_predictions = iso_forest.fit_predict(features_scaled)
                
                # Extract anomalies
                for i, (activity, prediction) in enumerate(zip(activities_list, anomaly_predictions)):
                    if prediction == -1:
                        anomaly_score = iso_forest.score_samples([features_scaled[i]])[0]
                        
                        # Determine anomaly type
                        if activity.duration_minutes > 180:  # More than 3 hours
                            anomaly_type = 'extremely_long_activity'
                            severity = 'medium'
                        elif activity.calories_burned > 1000:
                            anomaly_type = 'extremely_high_calorie_burn'
                            severity = 'medium'
                        else:
                            anomaly_type = 'irregular_activity_pattern'
                            severity = 'low'
                        
                        anomalies.append({
                            'activity_id': str(activity.id),
                            'date': activity.start_time.date(),
                            'activity_type': activity.activity_type,
                            'anomaly_type': anomaly_type,
                            'severity': severity,
                            'duration_minutes': activity.duration_minutes,
                            'calories_burned': activity.calories_burned,
                            'anomaly_score': float(anomaly_score)
                        })
        
        return anomalies
    
    def generate_anomaly_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive anomaly report"""
        
        report = {
            'period_days': days,
            'generated_at': self.now,
            'heart_rate_anomalies': [],
            'sleep_anomalies': [],
            'activity_anomalies': [],
            'summary': {},
            'recommendations': []
        }
        
        # Detect all types of anomalies
        heart_rate_anomalies = self.detect_heart_rate_anomalies(
            start_time=self.now - timedelta(days=days)
        )
        
        sleep_anomalies = self.detect_sleep_anomalies(days=days)
        
        activity_anomalies = self.detect_activity_anomalies(days=days)
        
        report['heart_rate_anomalies'] = heart_rate_anomalies
        report['sleep_anomalies'] = sleep_anomalies
        report['activity_anomalies'] = activity_anomalies
        
        # Generate summary
        total_anomalies = (
            len(heart_rate_anomalies) + 
            len(sleep_anomalies) + 
            len(activity_anomalies)
        )
        
        report['summary'] = {
            'total_anomalies': total_anomalies,
            'heart_rate_anomalies': len(heart_rate_anomalies),
            'sleep_anomalies': len(sleep_anomalies),
            'activity_anomalies': len(activity_anomalies),
            'anomaly_rate': round(total_anomalies / days, 2)
        }
        
        # Generate recommendations based on anomalies
        recommendations = []
        
        # Heart rate anomaly recommendations
        if heart_rate_anomalies:
            high_hr_anomalies = [a for a in heart_rate_anomalies if a['severity'] == 'high']
            if high_hr_anomalies:
                recommendations.append({
                    'category': 'heart_health',
                    'priority': 'high',
                    'title': 'Monitor Heart Rate Patterns',
                    'description': 'Multiple high-severity heart rate anomalies detected.',
                    'actions': [
                        'Consider consulting a healthcare provider',
                        'Monitor stress levels',
                        'Ensure proper hydration'
                    ]
                })
        
        # Sleep anomaly recommendations
        if sleep_anomalies:
            short_sleep_anomalies = [a for a in sleep_anomalies if a['anomaly_type'] == 'extremely_short_sleep']
            if short_sleep_anomalies:
                recommendations.append({
                    'category': 'sleep',
                    'priority': 'medium',
                    'title': 'Address Sleep Duration',
                    'description': 'Multiple instances of extremely short sleep detected.',
                    'actions': [
                        'Establish consistent bedtime routine',
                        'Create optimal sleep environment',
                        'Limit caffeine and screen time before bed'
                    ]
                })
        
        # Activity anomaly recommendations
        if activity_anomalies:
            long_activity_anomalies = [a for a in activity_anomalies if a['anomaly_type'] == 'extremely_long_activity']
            if long_activity_anomalies:
                recommendations.append({
                    'category': 'activity',
                    'priority': 'medium',
                    'title': 'Balance Activity Levels',
                    'description': 'Extremely long activity sessions detected.',
                    'actions': [
                        'Ensure adequate recovery between intense workouts',
                        'Listen to your body and avoid overtraining',
                        'Include rest days in your routine'
                    ]
                })
        
        report['recommendations'] = recommendations
        
        return report