from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import (
    HeartRateReading, SleepSession, Activity, DailySummary,
    HealthGoal, HealthAlert, HealthInsight
)


class HeartRateReadingSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    is_resting = serializers.BooleanField(read_only=True)
    is_elevated = serializers.BooleanField(read_only=True)
    is_low = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = HeartRateReading
        fields = [
            'id', 'user', 'device', 'device_name', 'bpm', 'timestamp',
            'confidence', 'context', 'is_anomaly', 'anomaly_type',
            'is_resting', 'is_elevated', 'is_low', 'raw_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_anomaly', 'anomaly_type']
    
    def validate_bpm(self, value):
        """Validate heart rate value"""
        if not 30 <= value <= 250:
            raise serializers.ValidationError("Heart rate must be between 30 and 250 BPM")
        return value
    
    def validate_timestamp(self, value):
        """Validate timestamp"""
        if value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError("Timestamp cannot be in the future")
        return value


class SleepSessionSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    total_sleep_minutes = serializers.IntegerField(read_only=True)
    deep_sleep_percentage = serializers.FloatField(read_only=True)
    rem_sleep_percentage = serializers.FloatField(read_only=True)
    sleep_hours = serializers.FloatField(read_only=True)
    
    class Meta:
        model = SleepSession
        fields = [
            'id', 'user', 'device', 'device_name', 'start_time', 'end_time',
            'duration_minutes', 'awake_minutes', 'light_minutes', 'deep_minutes',
            'rem_minutes', 'quality_score', 'quality_category', 'interruptions',
            'sleep_efficiency', 'average_heart_rate', 'minimum_heart_rate',
            'maximum_heart_rate', 'resting_heart_rate', 'was_restless',
            'had_insomnia', 'total_sleep_minutes', 'deep_sleep_percentage',
            'rem_sleep_percentage', 'sleep_hours', 'raw_data', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate sleep session data"""
        if data.get('start_time') and data.get('end_time'):
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })
            
            duration = (data['end_time'] - data['start_time']).total_seconds() / 60
            if duration > 1440:  # 24 hours
                raise serializers.ValidationError({
                    'duration': 'Sleep duration cannot exceed 24 hours'
                })
        
        # Validate sleep stage minutes
        stage_fields = ['awake_minutes', 'light_minutes', 'deep_minutes', 'rem_minutes']
        for field in stage_fields:
            if field in data and data[field] < 0:
                raise serializers.ValidationError({
                    field: f'{field} cannot be negative'
                })
        
        return data


class ActivitySerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    calories_per_minute = serializers.FloatField(read_only=True)
    is_cardio = serializers.BooleanField(read_only=True)
    is_strength = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Activity
        fields = [
            'id', 'user', 'device', 'device_name', 'activity_type', 'intensity',
            'start_time', 'end_time', 'duration_minutes', 'calories_burned',
            'distance_km', 'steps', 'avg_heart_rate', 'max_heart_rate',
            'min_heart_rate', 'heart_rate_zones', 'gps_coordinates',
            'elevation_gain', 'avg_speed_kmh', 'max_speed_kmh',
            'avg_pace_min_per_km', 'was_completed', 'perceived_exertion',
            'recovery_time_minutes', 'calories_per_minute', 'is_cardio',
            'is_strength', 'raw_data', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate activity data"""
        if data.get('start_time') and data.get('end_time'):
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })
            
            duration = (data['end_time'] - data['start_time']).total_seconds() / 60
            if duration > 1440:  # 24 hours
                raise serializers.ValidationError({
                    'duration': 'Activity duration cannot exceed 24 hours'
                })
        
        # Validate heart rate values
        heart_rate_fields = ['avg_heart_rate', 'max_heart_rate', 'min_heart_rate']
        for field in heart_rate_fields:
            if field in data and data[field] is not None:
                if not 30 <= data[field] <= 250:
                    raise serializers.ValidationError({
                        field: f'{field} must be between 30 and 250 BPM'
                    })
        
        return data


class DailySummarySerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    total_active_minutes = serializers.IntegerField(read_only=True)
    met_minutes = serializers.FloatField(read_only=True)
    sleep_hours = serializers.FloatField(read_only=True)
    is_healthy_day = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DailySummary
        fields = [
            'id', 'user', 'date', 'total_steps', 'total_calories', 'active_calories',
            'sedentary_minutes', 'light_active_minutes', 'moderately_active_minutes',
            'very_active_minutes', 'avg_heart_rate', 'min_heart_rate', 'max_heart_rate',
            'resting_heart_rate', 'heart_rate_variability', 'sleep_duration_minutes',
            'sleep_score', 'sleep_efficiency', 'time_to_sleep_minutes',
            'sleep_interruptions', 'weight_kg', 'body_fat_percentage',
            'muscle_mass_kg', 'bone_mass_kg', 'water_percentage',
            'blood_pressure_systolic', 'blood_pressure_diastolic', 'blood_oxygen',
            'body_temperature', 'respiratory_rate', 'stress_level', 'recovery_score',
            'readiness_score', 'menstrual_flow', 'menstrual_symptoms', 'overall_score',
            'insights', 'recommendations', 'total_active_minutes', 'met_minutes',
            'sleep_hours', 'is_healthy_day', 'is_complete', 'data_sources',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HealthGoalSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    progress_percentage = serializers.FloatField(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_on_track = serializers.SerializerMethodField()
    
    class Meta:
        model = HealthGoal
        fields = [
            'id', 'user', 'goal_type', 'name', 'description', 'target_value',
            'current_value', 'unit', 'progress_percentage', 'frequency',
            'start_date', 'end_date', 'is_completed', 'completed_at',
            'current_streak', 'longest_streak', 'is_active', 'is_primary',
            'reminder_enabled', 'reminder_time', 'days_remaining', 'is_on_track',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'progress_percentage']
    
    def get_days_remaining(self, obj):
        """Calculate days remaining until goal end date"""
        if obj.end_date:
            today = timezone.now().date()
            if obj.end_date >= today:
                return (obj.end_date - today).days
        return None
    
    def get_is_on_track(self, obj):
        """Check if goal is on track based on progress and time"""
        if not obj.end_date or not obj.start_date:
            return None
        
        today = timezone.now().date()
        total_days = (obj.end_date - obj.start_date).days
        days_passed = (today - obj.start_date).days
        
        if total_days > 0 and days_passed > 0:
            expected_progress = (days_passed / total_days) * 100
            return obj.progress_percentage >= expected_progress
        
        return None
    
    def validate(self, data):
        """Validate goal data"""
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        if data.get('target_value') <= 0:
            raise serializers.ValidationError({
                'target_value': 'Target value must be greater than 0'
            })
        
        return data


class HealthAlertSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = HealthAlert
        fields = [
            'id', 'user', 'alert_type', 'severity', 'title', 'message',
            'metric_value', 'metric_unit', 'threshold_value', 'related_model',
            'related_id', 'is_read', 'is_acknowledged', 'acknowledged_at',
            'sent_via_push', 'sent_via_email', 'sent_via_sms', 'triggered_at',
            'created_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'triggered_at', 'read_at', 'acknowledged_at',
            'sent_via_push', 'sent_via_email', 'sent_via_sms'
        ]


class HealthInsightSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    is_active = serializers.BooleanField(read_only=True)
    age_days = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = HealthInsight
        fields = [
            'id', 'user', 'insight_type', 'category', 'title', 'description',
            'confidence', 'data_points', 'visualization_data', 'start_date',
            'end_date', 'action_items', 'recommendations', 'is_new', 'is_applied',
            'is_dismissed', 'generated_by', 'generated_at', 'expires_at',
            'is_active', 'age_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'generated_at']


# Summary and aggregated serializers
class HealthMetricsSerializer(serializers.Serializer):
    """Serializer for current health metrics"""
    date = serializers.DateField()
    steps = serializers.IntegerField()
    calories_burned = serializers.FloatField()
    active_minutes = serializers.IntegerField()
    avg_heart_rate = serializers.FloatField(allow_null=True)
    resting_heart_rate = serializers.IntegerField(allow_null=True)
    sleep_duration = serializers.IntegerField(allow_null=True)
    sleep_score = serializers.FloatField(allow_null=True)
    weight = serializers.FloatField(allow_null=True)
    blood_pressure = serializers.CharField(allow_null=True)
    blood_oxygen = serializers.FloatField(allow_null=True)


class HealthTrendsSerializer(serializers.Serializer):
    """Serializer for health trends over time"""
    metric = serializers.CharField()
    unit = serializers.CharField()
    data = serializers.ListField(child=serializers.DictField())
    trend_direction = serializers.CharField(help_text="up, down, or stable")
    trend_strength = serializers.FloatField(help_text="0.0 to 1.0")
    current_value = serializers.FloatField()
    average_value = serializers.FloatField()
    change_percentage = serializers.FloatField(allow_null=True)


class HealthRecommendationSerializer(serializers.Serializer):
    """Serializer for health recommendations"""
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    priority = serializers.CharField(help_text="low, medium, high")
    action_items = serializers.ListField(child=serializers.CharField())
    expected_benefit = serializers.CharField()
    estimated_time = serializers.CharField()
    resources = serializers.ListField(child=serializers.URLField(), required=False)