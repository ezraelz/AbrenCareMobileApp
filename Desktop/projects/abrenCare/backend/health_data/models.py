# health_data/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class HeartRateReading(models.Model):
    """Individual heart rate readings"""
    
    HEART_RATE_CONTEXTS = (
        ('rest', 'Rest'),
        ('active', 'Active'),
        ('workout', 'Workout'),
        ('recovery', 'Recovery'),
        ('sleep', 'Sleep'),
        ('unknown', 'Unknown'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='heart_rate_readings'
    )
    device = models.ForeignKey(
        'devices.Device', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='heart_rate_readings'
    )
    
    # Core measurement
    bpm = models.IntegerField(help_text="Beats per minute")
    timestamp = models.DateTimeField(db_index=True)
    
    # Metadata
    confidence = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Device confidence level (0.0 to 1.0)"
    )
    context = models.CharField(
        max_length=20, 
        choices=HEART_RATE_CONTEXTS, 
        default='unknown'
    )
    
    # Processing fields
    is_anomaly = models.BooleanField(default=False)
    anomaly_type = models.CharField(max_length=50, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # For deduplication
    data_hash = models.CharField(max_length=64, db_index=True, blank=True)
    # CHANGE THIS LINE:
    raw_data = models.JSONField(default=dict, blank=True)  # Changed to models.JSONField
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'heart_rate_readings'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'is_anomaly']),
            models.Index(fields=['data_hash']),
        ]
        ordering = ['-timestamp']
        verbose_name = 'Heart Rate Reading'
        verbose_name_plural = 'Heart Rate Readings'
    
    def __str__(self):
        return f"{self.user.email}: {self.bpm} BPM at {self.timestamp}"
    
    @property
    def is_resting(self):
        """Check if this is a resting heart rate"""
        return self.context == 'rest' and 50 <= self.bpm <= 100
    
    @property
    def is_elevated(self):
        """Check if heart rate is elevated"""
        return self.bpm > 120 and self.context == 'rest'
    
    @property
    def is_low(self):
        """Check if heart rate is too low"""
        return self.bpm < 50 and self.context != 'sleep'


class SleepSession(models.Model):
    """Sleep sessions with detailed stage information"""
    
    SLEEP_QUALITY_CHOICES = (
        ('poor', 'Poor'),
        ('fair', 'Fair'),
        ('good', 'Good'),
        ('excellent', 'Excellent'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sleep_sessions'
    )
    device = models.ForeignKey(
        'devices.Device', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sleep_sessions'
    )
    
    # Timing
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    duration_minutes = models.IntegerField(help_text="Total sleep duration in minutes")
    
    # Sleep stages (in minutes)
    awake_minutes = models.IntegerField(default=0)
    light_minutes = models.IntegerField(default=0)
    deep_minutes = models.IntegerField(default=0)
    rem_minutes = models.IntegerField(default=0)
    
    # Sleep quality metrics
    quality_score = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Sleep quality score (0-100)"
    )
    quality_category = models.CharField(
        max_length=20, 
        choices=SLEEP_QUALITY_CHOICES, 
        blank=True
    )
    interruptions = models.IntegerField(default=0, help_text="Number of sleep interruptions")
    sleep_efficiency = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Sleep efficiency percentage (time asleep / time in bed)"
    )
    
    # Additional metrics
    average_heart_rate = models.IntegerField(null=True, blank=True)
    minimum_heart_rate = models.IntegerField(null=True, blank=True)
    maximum_heart_rate = models.IntegerField(null=True, blank=True)
    resting_heart_rate = models.IntegerField(null=True, blank=True)
    
    # Analysis fields
    was_restless = models.BooleanField(default=False)
    had_insomnia = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # For deduplication
    data_hash = models.CharField(max_length=64, db_index=True, blank=True)
    # CHANGE THIS LINE:
    raw_data = models.JSONField(default=dict, blank=True)  # Changed to models.JSONField
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sleep_sessions'
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['user', 'quality_score']),
            models.Index(fields=['data_hash']),
        ]
        ordering = ['-start_time']
        verbose_name = 'Sleep Session'
        verbose_name_plural = 'Sleep Sessions'
    
    def __str__(self):
        return f"{self.user.email}: Sleep from {self.start_time.date()}"
    
    def save(self, *args, **kwargs):
        # Calculate duration if not provided
        if not self.duration_minutes and self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds() / 60
            self.duration_minutes = int(duration)
        
        # Calculate sleep efficiency if not provided
        if not self.sleep_efficiency and self.duration_minutes > 0:
            total_minutes = self.awake_minutes + self.light_minutes + self.deep_minutes + self.rem_minutes
            if total_minutes > 0:
                self.sleep_efficiency = (total_minutes / self.duration_minutes) * 100
        
        # Set quality category based on score
        if self.quality_score and not self.quality_category:
            if self.quality_score >= 85:
                self.quality_category = 'excellent'
            elif self.quality_score >= 70:
                self.quality_category = 'good'
            elif self.quality_score >= 50:
                self.quality_category = 'fair'
            else:
                self.quality_category = 'poor'
        
        super().save(*args, **kwargs)
    
    @property
    def total_sleep_minutes(self):
        """Get total sleep minutes (excluding awake time)"""
        return self.light_minutes + self.deep_minutes + self.rem_minutes
    
    @property
    def deep_sleep_percentage(self):
        """Get percentage of deep sleep"""
        total = self.total_sleep_minutes
        return (self.deep_minutes / total * 100) if total > 0 else 0
    
    @property
    def rem_sleep_percentage(self):
        """Get percentage of REM sleep"""
        total = self.total_sleep_minutes
        return (self.rem_minutes / total * 100) if total > 0 else 0


class Activity(models.Model):
    """Physical activities and workouts"""
    
    ACTIVITY_TYPES = (
        ('walking', 'Walking'),
        ('running', 'Running'),
        ('cycling', 'Cycling'),
        ('swimming', 'Swimming'),
        ('hiking', 'Hiking'),
        ('yoga', 'Yoga'),
        ('strength_training', 'Strength Training'),
        ('hiit', 'HIIT'),
        ('dancing', 'Dancing'),
        ('sports', 'Sports'),
        ('workout', 'Generic Workout'),
        ('other', 'Other'),
    )
    
    INTENSITY_LEVELS = (
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('vigorous', 'Vigorous'),
        ('maximal', 'Maximal'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='activities'
    )
    device = models.ForeignKey(
        'devices.Device', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='activities'
    )
    
    # Activity information
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    intensity = models.CharField(max_length=20, choices=INTENSITY_LEVELS, blank=True)
    
    # Timing
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    duration_minutes = models.IntegerField()
    
    # Metrics
    calories_burned = models.FloatField(help_text="Calories burned during activity")
    distance_km = models.FloatField(null=True, blank=True, help_text="Distance in kilometers")
    steps = models.IntegerField(null=True, blank=True)
    
    # Heart rate metrics
    avg_heart_rate = models.IntegerField(null=True, blank=True)
    max_heart_rate = models.IntegerField(null=True, blank=True)
    min_heart_rate = models.IntegerField(null=True, blank=True)
    # CHANGE THIS LINE:
    heart_rate_zones = models.JSONField(default=dict, blank=True, help_text="Time spent in each HR zone")
    
    # GPS data
    # CHANGE THIS LINE:
    gps_coordinates = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Array of [lat, lng, altitude, timestamp]"
    )
    elevation_gain = models.FloatField(null=True, blank=True, help_text="Elevation gain in meters")
    
    # Performance metrics
    avg_speed_kmh = models.FloatField(null=True, blank=True)
    max_speed_kmh = models.FloatField(null=True, blank=True)
    avg_pace_min_per_km = models.FloatField(null=True, blank=True)
    
    # Analysis fields
    was_completed = models.BooleanField(default=True)
    perceived_exertion = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="RPE scale (1-10)"
    )
    recovery_time_minutes = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Estimated recovery time"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # For deduplication
    data_hash = models.CharField(max_length=64, db_index=True, blank=True)
    # CHANGE THIS LINE:
    raw_data = models.JSONField(default=dict, blank=True)  # Changed to models.JSONField
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'activities'
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['user', 'activity_type', 'start_time']),
            models.Index(fields=['data_hash']),
        ]
        ordering = ['-start_time']
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        return f"{self.user.email}: {self.activity_type} on {self.start_time.date()}"
    
    def save(self, *args, **kwargs):
        # Calculate duration if not provided
        if not self.duration_minutes and self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds() / 60
            self.duration_minutes = int(duration)
        
        # Calculate pace if distance and duration are available
        if not self.avg_pace_min_per_km and self.distance_km and self.duration_minutes > 0:
            self.avg_pace_min_per_km = self.duration_minutes / self.distance_km
        
        # Calculate average speed if distance and duration are available
        if not self.avg_speed_kmh and self.distance_km and self.duration_minutes > 0:
            self.avg_speed_kmh = (self.distance_km / self.duration_minutes) * 60
        
        super().save(*args, **kwargs)
    
    @property
    def calories_per_minute(self):
        """Get calories burned per minute"""
        return self.calories_burned / self.duration_minutes if self.duration_minutes > 0 else 0
    
    @property
    def is_cardio(self):
        """Check if activity is cardio-focused"""
        cardio_types = ['running', 'cycling', 'swimming', 'hiking', 'hiit']
        return self.activity_type in cardio_types
    
    @property
    def is_strength(self):
        """Check if activity is strength-focused"""
        return self.activity_type == 'strength_training'


class DailySummary(models.Model):
    """Daily aggregated health metrics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='daily_summaries'
    )
    
    # Date
    date = models.DateField(db_index=True)
    
    # Activity metrics
    total_steps = models.IntegerField(default=0)
    total_calories = models.FloatField(default=0, help_text="Total calories burned")
    active_calories = models.FloatField(default=0, help_text="Active calories burned")
    sedentary_minutes = models.IntegerField(default=0)
    light_active_minutes = models.IntegerField(default=0)
    moderately_active_minutes = models.IntegerField(default=0)
    very_active_minutes = models.IntegerField(default=0)
    
    # Heart rate metrics
    avg_heart_rate = models.FloatField(null=True, blank=True)
    min_heart_rate = models.IntegerField(null=True, blank=True)
    max_heart_rate = models.IntegerField(null=True, blank=True)
    resting_heart_rate = models.IntegerField(null=True, blank=True)
    heart_rate_variability = models.FloatField(
        null=True, 
        blank=True, 
        help_text="HRV in milliseconds"
    )
    
    # Sleep metrics
    sleep_duration_minutes = models.IntegerField(null=True, blank=True)
    sleep_score = models.FloatField(null=True, blank=True)
    sleep_efficiency = models.FloatField(null=True, blank=True)
    time_to_sleep_minutes = models.IntegerField(null=True, blank=True)
    sleep_interruptions = models.IntegerField(null=True, blank=True)
    
    # Health metrics
    weight_kg = models.FloatField(null=True, blank=True)
    body_fat_percentage = models.FloatField(null=True, blank=True)
    muscle_mass_kg = models.FloatField(null=True, blank=True)
    bone_mass_kg = models.FloatField(null=True, blank=True)
    water_percentage = models.FloatField(null=True, blank=True)
    
    # Vital signs
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    blood_oxygen = models.FloatField(null=True, blank=True, help_text="SpO2 percentage")
    body_temperature = models.FloatField(null=True, blank=True, help_text="Body temperature in Celsius")
    respiratory_rate = models.FloatField(null=True, blank=True, help_text="Breaths per minute")
    
    # Stress and recovery
    stress_level = models.FloatField(null=True, blank=True, help_text="Stress level (0-100)")
    recovery_score = models.FloatField(null=True, blank=True, help_text="Recovery score (0-100)")
    readiness_score = models.FloatField(null=True, blank=True, help_text="Readiness to perform (0-100)")
    
    # Menstrual cycle (for female users)
    menstrual_flow = models.CharField(
        max_length=20, 
        blank=True, 
        choices=[
            ('none', 'None'),
            ('light', 'Light'),
            ('medium', 'Medium'),
            ('heavy', 'Heavy'),
        ]
    )
    # CHANGE THIS LINE:
    menstrual_symptoms = models.JSONField(default=list, blank=True)
    
    # Analysis and insights
    overall_score = models.FloatField(null=True, blank=True, help_text="Overall daily health score (0-100)")
    # CHANGE THIS LINE:
    insights = models.JSONField(default=list, blank=True, help_text="Daily health insights")
    # CHANGE THIS LINE:
    recommendations = models.JSONField(default=list, blank=True, help_text="Health recommendations")
    
    # Metadata
    processed_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False, help_text="Whether all data for the day is complete")
    # CHANGE THIS LINE:
    data_sources = models.JSONField(default=list, blank=True, help_text="Sources of data for this day")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_summaries'
        unique_together = ['user', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['user', 'overall_score']),
        ]
        ordering = ['-date']
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summaries'
    
    def __str__(self):
        return f"{self.user.email}: Summary for {self.date}"
    
    @property
    def total_active_minutes(self):
        """Get total active minutes"""
        return (
            self.light_active_minutes + 
            self.moderately_active_minutes + 
            self.very_active_minutes
        )
    
    @property
    def met_minutes(self):
        """Get MET minutes (Metabolic Equivalent of Task)"""
        return (
            (self.light_active_minutes * 2) +
            (self.moderately_active_minutes * 4) +
            (self.very_active_minutes * 8)
        )
    
    @property
    def sleep_hours(self):
        """Get sleep duration in hours"""
        return self.sleep_duration_minutes / 60 if self.sleep_duration_minutes else None
    
    @property
    def is_healthy_day(self):
        """Check if this was a healthy day based on metrics"""
        if not self.overall_score:
            return None
        
        criteria = {
            'steps': self.total_steps >= 8000,
            'sleep': self.sleep_duration_minutes and self.sleep_duration_minutes >= 420,  # 7 hours
            'active_minutes': self.total_active_minutes >= 30,
            'score': self.overall_score >= 70
        }
        
        return all(criteria.values())
    

class HealthGoal(models.Model):
    """User health goals"""
    
    GOAL_TYPES = (
        ('steps', 'Daily Steps'),
        ('sleep', 'Sleep Duration'),
        ('weight', 'Weight'),
        ('activity', 'Activity Minutes'),
        ('heart_rate', 'Resting Heart Rate'),
        ('hydration', 'Water Intake'),
        ('calories', 'Calorie Intake/Burn'),
        ('meditation', 'Meditation'),
        ('workout', 'Workout Frequency'),
        ('custom', 'Custom'),
    )
    
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='health_goals'
    )
    
    # Goal definition
    goal_type = models.CharField(max_length=30, choices=GOAL_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Target values
    target_value = models.FloatField(help_text="Target value for the goal")
    current_value = models.FloatField(default=0, help_text="Current progress towards goal")
    unit = models.CharField(max_length=50, blank=True)
    
    # Timeframe
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Progress tracking
    progress_percentage = models.FloatField(default=0, help_text="Progress percentage (0-100)")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Streak tracking
    current_streak = models.IntegerField(default=0, help_text="Current consecutive days meeting goal")
    longest_streak = models.IntegerField(default=0, help_text="Longest consecutive days meeting goal")
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False, help_text="Primary goal shown on dashboard")
    reminder_enabled = models.BooleanField(default=False)
    reminder_time = models.TimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'health_goals'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'goal_type']),
            models.Index(fields=['user', 'is_primary']),
        ]
        ordering = ['-is_primary', '-created_at']
        verbose_name = 'Health Goal'
        verbose_name_plural = 'Health Goals'
    
    def __str__(self):
        return f"{self.user.email}: {self.name}"
    
    def save(self, *args, **kwargs):
        # Calculate progress percentage
        if self.target_value > 0:
            self.progress_percentage = min(100, (self.current_value / self.target_value) * 100)
        
        # Check if goal is completed
        if not self.is_completed and self.progress_percentage >= 100:
            self.is_completed = True
            self.completed_at = timezone.now()
        
        # Ensure only one primary goal per user
        if self.is_primary:
            HealthGoal.objects.filter(
                user=self.user, 
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        
        super().save(*args, **kwargs)
    
    @property
    def is_on_track(self):
        """Check if goal is on track based on timeline"""
        if not self.end_date:
            return None
        
        today = timezone.now().date()
        total_days = (self.end_date - self.start_date).days
        days_passed = (today - self.start_date).days
        
        if days_passed <= 0 or total_days <= 0:
            return None
        
        expected_progress = (days_passed / total_days) * 100
        return self.progress_percentage >= expected_progress
    
    @property
    def days_remaining(self):
        """Get days remaining until goal end date"""
        if self.end_date:
            today = timezone.now().date()
            remaining = (self.end_date - today).days
            return max(0, remaining) if remaining > 0 else 0
        return None


class HealthAlert(models.Model):
    """Health alerts and notifications"""
    
    ALERT_TYPES = (
        ('heart_rate_high', 'High Heart Rate'),
        ('heart_rate_low', 'Low Heart Rate'),
        ('sleep_poor', 'Poor Sleep'),
        ('inactivity', 'Inactivity'),
        ('goal_achieved', 'Goal Achieved'),
        ('goal_progress', 'Goal Progress'),
        ('medication', 'Medication Reminder'),
        ('hydration', 'Hydration Reminder'),
        ('stress_high', 'High Stress'),
        ('blood_pressure', 'Blood Pressure Alert'),
        ('blood_oxygen', 'Blood Oxygen Alert'),
        ('irregular_rhythm', 'Irregular Heart Rhythm'),
        ('fall_detected', 'Fall Detected'),
        ('custom', 'Custom Alert'),
    )
    
    SEVERITY_LEVELS = (
        ('info', 'Information'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='health_alerts'
    )
    
    # Alert information
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Alert data
    metric_value = models.FloatField(null=True, blank=True)
    metric_unit = models.CharField(max_length=50, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    
    # Related data
    related_model = models.CharField(max_length=50, blank=True)
    related_id = models.CharField(max_length=100, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery
    sent_via_push = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)
    sent_via_sms = models.BooleanField(default=False)
    
    # Timestamps
    triggered_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'health_alerts'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'alert_type']),
            models.Index(fields=['user', 'severity']),
            models.Index(fields=['triggered_at']),
        ]
        ordering = ['-triggered_at']
        verbose_name = 'Health Alert'
        verbose_name_plural = 'Health Alerts'
    
    def __str__(self):
        return f"{self.user.email}: {self.alert_type} - {self.title}"
    
    def mark_as_read(self):
        """Mark alert as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    def acknowledge(self):
        """Acknowledge the alert"""
        self.is_acknowledged = True
        self.acknowledged_at = timezone.now()
        self.save()


class HealthInsight(models.Model):
    """Generated health insights and patterns"""
    
    INSIGHT_TYPES = (
        ('trend', 'Trend'),
        ('pattern', 'Pattern'),
        ('correlation', 'Correlation'),
        ('anomaly', 'Anomaly'),
        ('recommendation', 'Recommendation'),
        ('achievement', 'Achievement'),
        ('warning', 'Warning'),
        ('prediction', 'Prediction'),
    )
    
    CATEGORIES = (
        ('activity', 'Activity'),
        ('sleep', 'Sleep'),
        ('heart', 'Heart Health'),
        ('nutrition', 'Nutrition'),
        ('stress', 'Stress'),
        ('recovery', 'Recovery'),
        ('overall', 'Overall Health'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='health_insights'
    )
    
    # Insight information
    insight_type = models.CharField(max_length=30, choices=INSIGHT_TYPES)
    category = models.CharField(max_length=30, choices=CATEGORIES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Insight data
    confidence = models.FloatField(default=0.8, help_text="Confidence level (0.0 to 1.0)")
    # CHANGE THESE LINES:
    data_points = models.JSONField(default=dict, blank=True, help_text="Supporting data for the insight")
    visualization_data = models.JSONField(default=dict, blank=True, help_text="Data for charts/visualizations")
    
    # Time period
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Actions and recommendations
    # CHANGE THESE LINES:
    action_items = models.JSONField(default=list, blank=True, help_text="Suggested actions")
    recommendations = models.JSONField(default=list, blank=True)
    
    # Status
    is_new = models.BooleanField(default=True)
    is_applied = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    
    # Metadata
    generated_by = models.CharField(
        max_length=50, 
        choices=[
            ('system', 'System'),
            ('ai', 'AI Model'),
            ('doctor', 'Doctor'),
            ('user', 'User'),
        ],
        default='system'
    )
    generated_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'health_insights'
        indexes = [
            models.Index(fields=['user', 'is_new']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'insight_type']),
            models.Index(fields=['generated_at']),
        ]
        ordering = ['-is_new', '-generated_at']
        verbose_name = 'Health Insight'
        verbose_name_plural = 'Health Insights'
    
    def __str__(self):
        return f"{self.user.email}: {self.title}"
    
    def mark_as_read(self):
        """Mark insight as read (not new)"""
        self.is_new = False
        self.save()
    
    def apply_insight(self):
        """Mark insight as applied"""
        self.is_applied = True
        self.save()
    
    def dismiss(self):
        """Dismiss the insight"""
        self.is_dismissed = True
        self.save()
    
    @property
    def is_active(self):
        """Check if insight is still active/valid"""
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True
    
    @property
    def age_days(self):
        """Get age of insight in days"""
        return (timezone.now() - self.generated_at).days
    