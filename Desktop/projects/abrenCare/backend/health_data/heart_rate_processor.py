import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from django.db.models import Avg, StdDev, Count, Q

from .models import HeartRateReading

logger = logging.getLogger(__name__)


class HeartRateProcessor:
    """Process and analyze heart rate data"""
    
    @staticmethod
    def detect_anomalies(
        user, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None,
        window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect abnormal heart rate patterns"""
        
        if not start_time:
            start_time = timezone.now() - timedelta(hours=window_hours)
        if not end_time:
            end_time = timezone.now()
        
        # Get readings in the time window
        readings = HeartRateReading.objects.filter(
            user=user,
            timestamp__range=[start_time, end_time]
        ).order_by('timestamp')
        
        if len(readings) < 10:  # Need enough data for analysis
            return []
        
        bpm_values = [r.bpm for r in readings]
        
        # Calculate statistics
        mean_bpm = np.mean(bpm_values)
        std_bpm = np.std(bpm_values)
        
        anomalies = []
        
        # Detect individual anomalies
        for reading in readings:
            z_score = (reading.bpm - mean_bpm) / std_bpm if std_bpm > 0 else 0
            
            # Detect extreme values
            if abs(z_score) > 3:
                anomaly_type = 'high_heart_rate' if z_score > 0 else 'low_heart_rate'
                severity = 'critical' if abs(z_score) > 4 else 'high'
                
                anomalies.append({
                    'type': anomaly_type,
                    'value': reading.bpm,
                    'timestamp': reading.timestamp,
                    'z_score': round(z_score, 2),
                    'severity': severity,
                    'context': reading.context,
                    'reading_id': str(reading.id)
                })
        
        # Detect patterns
        pattern_anomalies = HeartRateProcessor._detect_patterns(readings, mean_bpm, std_bpm)
        anomalies.extend(pattern_anomalies)
        
        # Update anomaly flags in database
        HeartRateProcessor._mark_anomalies_in_database(anomalies)
        
        return anomalies
    
    @staticmethod
    def _detect_patterns(
        readings: List[HeartRateReading], 
        mean_bpm: float, 
        std_bpm: float
    ) -> List[Dict[str, Any]]:
        """Detect heart rate patterns and trends"""
        anomalies = []
        
        if len(readings) < 20:
            return anomalies
        
        # Detect sustained high/low heart rate
        window_size = 10
        for i in range(len(readings) - window_size + 1):
            window = readings[i:i + window_size]
            window_values = [r.bpm for r in window]
            window_mean = np.mean(window_values)
            
            # Check for sustained high heart rate
            if window_mean > mean_bpm + 2 * std_bpm:
                anomalies.append({
                    'type': 'sustained_high_heart_rate',
                    'average_value': round(window_mean, 1),
                    'start_time': window[0].timestamp,
                    'end_time': window[-1].timestamp,
                    'duration_minutes': (window[-1].timestamp - window[0].timestamp).total_seconds() / 60,
                    'severity': 'medium',
                    'context': 'sustained_high'
                })
                break  # Only report the first sustained anomaly
        
        # Detect heart rate variability issues
        hrv_anomalies = HeartRateProcessor._detect_hrv_issues(readings)
        anomalies.extend(hrv_anomalies)
        
        return anomalies
    
    @staticmethod
    def _detect_hrv_issues(readings: List[HeartRateReading]) -> List[Dict[str, Any]]:
        """Detect heart rate variability issues"""
        anomalies = []
        
        if len(readings) < 30:  # Need enough data for HRV analysis
            return anomalies
        
        # Calculate RR intervals (time between beats)
        timestamps = [r.timestamp for r in readings]
        rr_intervals = []
        
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            rr_intervals.append(interval)
        
        if len(rr_intervals) < 20:
            return anomalies
        
        # Calculate HRV metrics
        rr_intervals_np = np.array(rr_intervals)
        
        # RMSSD (Root Mean Square of Successive Differences)
        differences = np.diff(rr_intervals_np)
        squared_diff = np.square(differences)
        mean_squared = np.mean(squared_diff)
        rmssd = np.sqrt(mean_squared) * 1000  # Convert to milliseconds
        
        # SDNN (Standard Deviation of NN intervals)
        sdnn = np.std(rr_intervals_np) * 1000  # Convert to milliseconds
        
        # Normal HRV ranges (varies by age, sex, etc.)
        low_hrv_threshold = 20  # ms for RMSSD
        very_low_hrv_threshold = 10  # ms for RMSSD
        
        if rmssd < very_low_hrv_threshold:
            anomalies.append({
                'type': 'very_low_hrv',
                'value': round(rmssd, 1),
                'unit': 'ms',
                'metric': 'RMSSD',
                'threshold': very_low_hrv_threshold,
                'severity': 'high',
                'timestamp': readings[-1].timestamp,
                'interpretation': 'Very low HRV may indicate high stress, fatigue, or illness'
            })
        elif rmssd < low_hrv_threshold:
            anomalies.append({
                'type': 'low_hrv',
                'value': round(rmssd, 1),
                'unit': 'ms',
                'metric': 'RMSSD',
                'threshold': low_hrv_threshold,
                'severity': 'medium',
                'timestamp': readings[-1].timestamp,
                'interpretation': 'Low HRV may indicate increased stress or poor recovery'
            })
        
        return anomalies
    
    @staticmethod
    def _mark_anomalies_in_database(anomalies: List[Dict[str, Any]]):
        """Mark anomalies in the database"""
        for anomaly in anomalies:
            if 'reading_id' in anomaly:
                try:
                    reading = HeartRateReading.objects.get(id=anomaly['reading_id'])
                    reading.is_anomaly = True
                    reading.anomaly_type = anomaly['type']
                    reading.save()
                except HeartRateReading.DoesNotExist:
                    continue
    
    @staticmethod
    def calculate_resting_heart_rate(user, date: datetime = None) -> Optional[Dict[str, Any]]:
        """Calculate resting heart rate for a user"""
        if not date:
            date = timezone.now().date()
        
        # Get resting heart rate readings from last night's sleep period
        # Typically measured during sleep or upon waking
        start_time = datetime.combine(date, datetime.min.time()) - timedelta(days=1)
        end_time = datetime.combine(date, datetime.min.time())
        
        # Get readings from sleep context or early morning
        readings = HeartRateReading.objects.filter(
            user=user,
            timestamp__range=[start_time, end_time],
            context__in=['sleep', 'rest']
        ).order_by('timestamp')
        
        if len(readings) < 5:
            return None
        
        # Take the lowest readings during rest/sleep
        bpm_values = [r.bpm for r in readings]
        lowest_readings = sorted(bpm_values)[:5]  # Get 5 lowest readings
        resting_hr = np.mean(lowest_readings)
        
        # Calculate trend if we have previous data
        previous_day = HeartRateProcessor.calculate_resting_heart_rate(
            user, date - timedelta(days=1)
        )
        
        trend = None
        if previous_day:
            change = resting_hr - previous_day['value']
            trend = 'up' if change > 0 else 'down' if change < 0 else 'stable'
        
        return {
            'value': round(resting_hr, 1),
            'unit': 'bpm',
            'timestamp': end_time,
            'readings_count': len(readings),
            'confidence': min(1.0, len(readings) / 20),  # Confidence based on data points
            'trend': trend,
            'optimal_range': (50, 70),  # Optimal resting HR range
            'interpretation': HeartRateProcessor._interpret_resting_hr(resting_hr)
        }
    
    @staticmethod
    def _interpret_resting_hr(hr: float) -> str:
        """Interpret resting heart rate value"""
        if hr < 40:
            return "Very low. Consult a healthcare provider."
        elif hr < 50:
            return "Low. May indicate good fitness or bradycardia."
        elif hr < 60:
            return "Excellent. Indicates good cardiovascular fitness."
        elif hr < 70:
            return "Good. Within healthy range."
        elif hr < 80:
            return "Average. Consider more cardiovascular exercise."
        elif hr < 90:
            return "Above average. May benefit from lifestyle improvements."
        else:
            return "High. Consider consulting a healthcare provider."
    
    @staticmethod
    def calculate_heart_rate_zones(user, activity_start: datetime, activity_end: datetime) -> Dict[str, Any]:
        """Calculate heart rate zones for an activity period"""
        
        # Get heart rate readings during activity
        readings = HeartRateReading.objects.filter(
            user=user,
            timestamp__range=[activity_start, activity_end]
        ).order_by('timestamp')
        
        if len(readings) < 10:
            return {}
        
        # Calculate max heart rate (estimated: 220 - age)
        # In production, you would get user's age from profile
        estimated_max_hr = 180  # Default, should be user-specific
        
        # Define HR zones as percentage of max HR
        zones = {
            'zone_1_recovery': (0.50, 0.60),    # 50-60% - Very light, recovery
            'zone_2_aerobic': (0.60, 0.70),     # 60-70% - Light, fat burning
            'zone_3_aerobic': (0.70, 0.80),     # 70-80% - Moderate, aerobic
            'zone_4_anaerobic': (0.80, 0.90),   # 80-90% - Hard, anaerobic
            'zone_5_maximum': (0.90, 1.00),     # 90-100% - Maximum effort
        }
        
        # Calculate time spent in each zone
        zone_times = {zone_name: 0 for zone_name in zones.keys()}
        zone_counts = {zone_name: 0 for zone_name in zones.keys()}
        
        for i in range(len(readings) - 1):
            reading = readings[i]
            next_reading = readings[i + 1]
            
            # Time between readings in seconds
            time_diff = (next_reading.timestamp - reading.timestamp).total_seconds()
            
            # Calculate HR as percentage of max
            hr_percentage = reading.bpm / estimated_max_hr
            
            # Determine which zone this reading falls into
            for zone_name, (min_percent, max_percent) in zones.items():
                if min_percent <= hr_percentage < max_percent:
                    zone_times[zone_name] += time_diff
                    zone_counts[zone_name] += 1
                    break
        
        # Convert times to minutes
        zone_times_minutes = {
            zone_name: round(time_seconds / 60, 1)
            for zone_name, time_seconds in zone_times.items()
        }
        
        # Calculate percentages
        total_time = sum(zone_times.values())
        zone_percentages = {
            zone_name: round((time_seconds / total_time * 100) if total_time > 0 else 0, 1)
            for zone_name, time_seconds in zone_times.items()
        }
        
        return {
            'zones': zones,
            'time_in_zones_minutes': zone_times_minutes,
            'percentage_in_zones': zone_percentages,
            'estimated_max_hr': estimated_max_hr,
            'average_hr': round(np.mean([r.bpm for r in readings]), 1),
            'max_hr': max([r.bpm for r in readings]),
            'min_hr': min([r.bpm for r in readings]),
            'total_readings': len(readings),
            'total_time_minutes': round(total_time / 60, 1)
        }
    
    @staticmethod
    def get_heart_rate_trends(
        user, 
        days: int = 7, 
        metric: str = 'avg_heart_rate'
    ) -> Dict[str, Any]:
        """Get heart rate trends over time"""
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Aggregate heart rate data by day
        from django.db.models import Avg, Min, Max
        
        daily_stats = HeartRateReading.objects.filter(
            user=user,
            timestamp__date__range=[start_date, end_date]
        ).extra({'date': "date(timestamp)"}).values('date').annotate(
            avg_bpm=Avg('bpm'),
            min_bpm=Min('bpm'),
            max_bpm=Max('bpm'),
            count=Count('id')
        ).order_by('date')
        
        if not daily_stats:
            return {}
        
        # Calculate overall statistics
        all_readings = HeartRateReading.objects.filter(
            user=user,
            timestamp__date__range=[start_date, end_date]
        )
        
        if not all_readings.exists():
            return {}
        
        all_bpm = [r.bpm for r in all_readings]
        
        trend_data = {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'overall': {
                'average': round(np.mean(all_bpm), 1),
                'minimum': min(all_bpm),
                'maximum': max(all_bpm),
                'std_dev': round(np.std(all_bpm), 1),
                'total_readings': len(all_bpm)
            },
            'daily_data': list(daily_stats),
            'trend_analysis': HeartRateProcessor._analyze_trend(all_bpm)
        }
        
        return trend_data
    
    @staticmethod
    def _analyze_trend(bpm_values: List[float]) -> Dict[str, Any]:
        """Analyze trend in heart rate data"""
        if len(bpm_values) < 2:
            return {'direction': 'insufficient_data', 'strength': 0}
        
        # Simple linear regression for trend
        x = np.arange(len(bpm_values))
        y = np.array(bpm_values)
        
        # Calculate slope
        slope, intercept = np.polyfit(x, y, 1)
        
        # Determine trend direction
        if slope > 0.1:
            direction = 'up'
        elif slope < -0.1:
            direction = 'down'
        else:
            direction = 'stable'
        
        # Calculate R-squared for trend strength
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {
            'direction': direction,
            'strength': round(r_squared, 3),
            'slope': round(slope, 3),
            'interpretation': HeartRateProcessor._interpret_trend(direction, r_squared)
        }
    
    @staticmethod
    def _interpret_trend(direction: str, strength: float) -> str:
        """Interpret the trend direction and strength"""
        if strength < 0.3:
            return "No clear trend detected."
        
        if direction == 'up':
            return "Heart rate showing an increasing trend. This may indicate increased stress, dehydration, or illness."
        elif direction == 'down':
            return "Heart rate showing a decreasing trend. This may indicate improving fitness or better recovery."
        else:
            return "Heart rate is stable, which is generally a positive sign."