from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from django.contrib.admin import SimpleListFilter
import json

from .models import (
    HeartRateReading, SleepSession, Activity, DailySummary,
    HealthGoal, HealthAlert, HealthInsight
)


# ============================================================
# CUSTOM FILTERS
# ============================================================

class DateRangeFilter(SimpleListFilter):
    title = 'Date Range'
    parameter_name = 'date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('last_7_days', 'Last 7 Days'),
            ('this_month', 'This Month'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        elif self.value() == 'yesterday':
            yesterday = today - timezone.timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        elif self.value() == 'last_7_days':
            return queryset.filter(created_at__date__gte=today - timezone.timedelta(days=7))
        elif self.value() == 'this_month':
            return queryset.filter(created_at__month=today.month, created_at__year=today.year)


class HealthScoreFilter(SimpleListFilter):
    title = 'Health Score'
    parameter_name = 'health_score'

    def lookups(self, request, model_admin):
        return [
            ('excellent', 'Excellent (≥85)'),
            ('good', 'Good (70-84)'),
            ('fair', 'Fair (50-69)'),
            ('poor', 'Poor (<50)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'excellent':
            return queryset.filter(overall_score__gte=85)
        elif self.value() == 'good':
            return queryset.filter(overall_score__gte=70, overall_score__lt=85)
        elif self.value() == 'fair':
            return queryset.filter(overall_score__gte=50, overall_score__lt=70)
        elif self.value() == 'poor':
            return queryset.filter(overall_score__lt=50)

# ============================================================
# ADMIN CLASSES
# ============================================================

@admin.register(HeartRateReading)
class HeartRateReadingAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'bpm_display', 'timestamp_short', 'context_badge', 
                    'is_anomaly_badge', 'created_at_short')
    list_filter = ('context', DateRangeFilter, 'user', 'is_anomaly')
    search_fields = ('user__email', 'context', 'anomaly_type')
    readonly_fields = ('created_at', 'updated_at', 'bpm_display', 'data_hash')
    list_per_page = 50
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'device', 'bpm_display', 'timestamp')
        }),
        ('Metadata', {
            'fields': ('confidence', 'context', 'is_anomaly', 'anomaly_type')
        }),
        ('Technical', {
            'fields': ('data_hash', 'raw_data', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def bpm_display(self, obj):
        color = 'green'
        if obj.is_elevated:
            color = 'orange'
        elif obj.is_low:
            color = 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{} bpm</span>', 
                          color, obj.bpm)
    bpm_display.short_description = 'BPM'
    
    def timestamp_short(self, obj):
        return obj.timestamp.strftime('%b %d, %H:%M')
    timestamp_short.short_description = 'Time'
    timestamp_short.admin_order_field = 'timestamp'
    
    def context_badge(self, obj):
        colors = {
            'rest': 'blue',
            'active': 'green',
            'workout': 'orange',
            'sleep': 'purple',
            'recovery': 'teal',
            'unknown': 'gray'
        }
        color = colors.get(obj.context, 'gray')
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{}</span>',
                          color, obj.get_context_display())
    context_badge.short_description = 'Context'
    
    def is_anomaly_badge(self, obj):
        if obj.is_anomaly:
            return format_html('<span style="background-color: #dc3545; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">ANOMALY</span>')
        return format_html('<span style="background-color: #28a745; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">Normal</span>')
    is_anomaly_badge.short_description = 'Status'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%b %d')
    created_at_short.short_description = 'Recorded'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'device')


@admin.register(SleepSession)
class SleepSessionAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'date_display', 'duration_display', 
                    'quality_score_progress', 'sleep_efficiency_badge', 'created_at_short')
    list_filter = ('quality_category', DateRangeFilter, 'user')
    search_fields = ('user__email', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'duration_display', 
                      'sleep_stages_summary', 'total_sleep_display')
    list_per_page = 30
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'device', 'start_time', 'end_time', 'duration_display')
        }),
        ('Sleep Stages', {
            'fields': ('awake_minutes', 'light_minutes', 'deep_minutes', 'rem_minutes',
                      'sleep_stages_summary'),
            'classes': ('wide',)
        }),
        ('Quality Metrics', {
            'fields': ('quality_score', 'quality_category', 'sleep_efficiency', 
                      'total_sleep_display', 'interruptions')
        }),
        ('Heart Rate During Sleep', {
            'fields': ('average_heart_rate', 'minimum_heart_rate', 'maximum_heart_rate', 
                      'resting_heart_rate'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('notes', 'was_restless', 'had_insomnia'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def date_display(self, obj):
        return obj.start_time.strftime('%b %d, %Y')
    date_display.short_description = 'Date'
    date_display.admin_order_field = 'start_time'
    
    def duration_display(self, obj):
        hours = obj.duration_minutes // 60
        minutes = obj.duration_minutes % 60
        return f"{hours}h {minutes}m"
    duration_display.short_description = 'Duration'
    
    def total_sleep_display(self, obj):
        return f"{obj.total_sleep_minutes} min"
    total_sleep_display.short_description = 'Total Sleep'
    
    def sleep_stages_summary(self, obj):
        stages = [
            f"Light: {obj.light_minutes}min",
            f"Deep: {obj.deep_minutes}min",
            f"REM: {obj.rem_minutes}min",
            f"Awake: {obj.awake_minutes}min"
        ]
        return ', '.join(stages)
    sleep_stages_summary.short_description = 'Stages Summary'
    
    def quality_score_progress(self, obj):
        if obj.quality_score:
            width = min(obj.quality_score, 100)
            color = '#dc3545'  # red
            if obj.quality_score >= 85:
                color = '#28a745'  # green
            elif obj.quality_score >= 70:
                color = '#ffc107'  # yellow
            
            return format_html(
                '<div style="width: 100px; height: 20px; background-color: #e9ecef; '
                'border-radius: 3px; overflow: hidden; position: relative;">'
                '<div style="width: {}%; height: 100%; background-color: {};">'
                '</div><span style="position: absolute; top: 0; left: 0; width: 100%; '
                'text-align: center; line-height: 20px; font-size: 12px; color: #000;">'
                '{:.0f}</span></div>',
                width, color, obj.quality_score
            )
        return "N/A"
    quality_score_progress.short_description = 'Quality Score'
    
    def sleep_efficiency_badge(self, obj):
        if obj.sleep_efficiency:
            color = '#28a745' if obj.sleep_efficiency >= 85 else '#ffc107'
            return format_html('<span style="background-color: {}; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">{:.1f}%</span>',
                              color, obj.sleep_efficiency)
        return "N/A"
    sleep_efficiency_badge.short_description = 'Efficiency'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%b %d')
    created_at_short.short_description = 'Recorded'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'device')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'activity_type_badge', 'date_display', 
                    'duration_display', 'calories_display', 'intensity_badge')
    list_filter = ('activity_type', 'intensity', DateRangeFilter, 'user')
    search_fields = ('user__email', 'activity_type', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'duration_display', 
                      'calories_per_minute_display', 'pace_display')
    list_per_page = 30
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'device', 'activity_type', 'intensity', 
                      'duration_display')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time')
        }),
        ('Metrics', {
            'fields': ('calories_burned', 'distance_km', 'steps', 
                      'calories_per_minute_display', 'pace_display')
        }),
        ('Heart Rate', {
            'fields': ('avg_heart_rate', 'max_heart_rate', 'min_heart_rate'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('notes', 'perceived_exertion', 'recovery_time_minutes'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def activity_type_badge(self, obj):
        colors = {
            'running': '#dc3545',
            'walking': '#28a745',
            'cycling': '#007bff',
            'swimming': '#17a2b8',
            'yoga': '#6f42c1',
            'strength_training': '#fd7e14',
        }
        color = colors.get(obj.activity_type, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{}</span>',
                          color, obj.get_activity_type_display())
    activity_type_badge.short_description = 'Activity'
    
    def date_display(self, obj):
        return obj.start_time.strftime('%b %d')
    date_display.short_description = 'Date'
    date_display.admin_order_field = 'start_time'
    
    def duration_display(self, obj):
        return f"{obj.duration_minutes} min"
    duration_display.short_description = 'Duration'
    
    def calories_display(self, obj):
        return f"{int(obj.calories_burned)} cal"
    calories_display.short_description = 'Calories'
    
    def calories_per_minute_display(self, obj):
        if obj.duration_minutes > 0:
            return f"{obj.calories_per_minute:.1f} cal/min"
        return "N/A"
    calories_per_minute_display.short_description = 'Calories per Minute'
    
    def pace_display(self, obj):
        if obj.avg_pace_min_per_km:
            return f"{obj.avg_pace_min_per_km:.2f} min/km"
        return "N/A"
    pace_display.short_description = 'Average Pace'
    
    def intensity_badge(self, obj):
        colors = {
            'low': '#28a745',
            'moderate': '#ffc107',
            'vigorous': '#fd7e14',
            'maximal': '#dc3545'
        }
        color = colors.get(obj.intensity, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{}</span>',
                          color, obj.get_intensity_display())
    intensity_badge.short_description = 'Intensity'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'device')


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'date_display', 'steps_progress', 
                    'calories_display', 'sleep_display', 'overall_score_progress', 
                    'complete_badge')
    list_filter = (HealthScoreFilter, DateRangeFilter, 'is_complete', 'user')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at', 'health_metrics_summary',
                      'activity_summary', 'sleep_summary')
    list_per_page = 20
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'date', 'is_complete')
        }),
        ('Activity Summary', {
            'fields': ('activity_summary', 'total_steps', 'total_calories')
        }),
        ('Sleep Summary', {
            'fields': ('sleep_summary', 'sleep_duration_minutes', 'sleep_score')
        }),
        ('Health Metrics', {
            'fields': ('health_metrics_summary', 'overall_score', 
                      'resting_heart_rate', 'stress_level'),
            'classes': ('wide',)
        }),
        ('Detailed Metrics', {
            'fields': ('heart_rate_variability', 'body_fat_percentage',
                      'blood_pressure_systolic', 'blood_pressure_diastolic'),
            'classes': ('collapse',)
        }),
        ('Insights & Recommendations', {
            'fields': ('insights', 'recommendations'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def date_display(self, obj):
        return obj.date.strftime('%b %d, %Y')
    date_display.short_description = 'Date'
    date_display.admin_order_field = 'date'
    
    def steps_progress(self, obj):
        width = min(obj.total_steps / 100, 100)  # Assuming 10000 steps as 100%
        color = '#28a745' if obj.total_steps >= 8000 else '#ffc107'
        return format_html(
            '<div style="width: 80px; height: 20px; background-color: #e9ecef; '
            'border-radius: 3px; overflow: hidden; position: relative;">'
            '<div style="width: {}%; height: 100%; background-color: {};">'
            '</div><span style="position: absolute; top: 0; left: 0; width: 100%; '
            'text-align: center; line-height: 20px; font-size: 12px; color: #000;">'
            '{:,}</span></div>',
            width, color, obj.total_steps
        )
    steps_progress.short_description = 'Steps'
    
    def calories_display(self, obj):
        return f"{int(obj.total_calories)} cal"
    calories_display.short_description = 'Calories'
    
    def sleep_display(self, obj):
        if obj.sleep_duration_minutes:
            hours = obj.sleep_duration_minutes // 60
            minutes = obj.sleep_duration_minutes % 60
            return f"{hours}h{minutes}m"
        return "N/A"
    sleep_display.short_description = 'Sleep'
    
    def overall_score_progress(self, obj):
        if obj.overall_score:
            width = min(obj.overall_score, 100)
            color = '#dc3545'  # red
            if obj.overall_score >= 85:
                color = '#28a745'  # green
            elif obj.overall_score >= 70:
                color = '#ffc107'  # yellow
            
            return format_html(
                '<div style="width: 80px; height: 20px; background-color: #e9ecef; '
                'border-radius: 3px; overflow: hidden; position: relative;">'
                '<div style="width: {}%; height: 100%; background-color: {};">'
                '</div><span style="position: absolute; top: 0; left: 0; width: 100%; '
                'text-align: center; line-height: 20px; font-size: 12px; color: #000;">'
                '{:.0f}</span></div>',
                width, color, obj.overall_score
            )
        return "N/A"
    overall_score_progress.short_description = 'Score'
    
    def complete_badge(self, obj):
        if obj.is_complete:
            return format_html('<span style="background-color: #28a745; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">✓ Complete</span>')
        return format_html('<span style="background-color: #6c757d; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">Incomplete</span>')
    complete_badge.short_description = 'Status'
    
    def health_metrics_summary(self, obj):
        metrics = []
        if obj.resting_heart_rate:
            metrics.append(f"Resting HR: {obj.resting_heart_rate}")
        if obj.blood_pressure_systolic and obj.blood_pressure_diastolic:
            metrics.append(f"BP: {obj.blood_pressure_systolic}/{obj.blood_pressure_diastolic}")
        if obj.body_fat_percentage:
            metrics.append(f"Body Fat: {obj.body_fat_percentage:.1f}%")
        
        return ', '.join(metrics) if metrics else "No metrics available"
    health_metrics_summary.short_description = 'Health Metrics'
    
    def activity_summary(self, obj):
        return f"Steps: {obj.total_steps:,}, Active: {obj.total_active_minutes}min"
    activity_summary.short_description = 'Activity'
    
    def sleep_summary(self, obj):
        if obj.sleep_duration_minutes:
            hours = obj.sleep_duration_minutes // 60
            minutes = obj.sleep_duration_minutes % 60
            score = f", Score: {obj.sleep_score:.0f}" if obj.sleep_score else ""
            return f"{hours}h{minutes}m{score}"
        return "No sleep data"
    sleep_summary.short_description = 'Sleep'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(HealthGoal)
class HealthGoalAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'name_short', 'goal_type_badge', 'progress_bar', 
                    'target_display', 'status_badge')
    list_filter = ('goal_type', 'frequency', 'is_active', 'is_completed', 'user')
    search_fields = ('user__email', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'progress_bar_display', 
                      'days_remaining_display', 'streak_display')
    list_per_page = 30
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'goal_type', 'name', 'description')
        }),
        ('Progress', {
            'fields': ('progress_bar_display', 'current_value', 'target_value', 'unit')
        }),
        ('Timeframe', {
            'fields': ('frequency', 'start_date', 'end_date', 'days_remaining_display')
        }),
        ('Status', {
            'fields': ('is_active', 'is_completed', 'completed_at', 'streak_display')
        }),
        ('Settings', {
            'fields': ('is_primary', 'reminder_enabled', 'reminder_time'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_completed', 'mark_incomplete', 'activate_goals', 'deactivate_goals']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def name_short(self, obj):
        return obj.name[:50] + '...' if len(obj.name) > 50 else obj.name
    name_short.short_description = 'Name'
    
    def goal_type_badge(self, obj):
        colors = {
            'steps': '#28a745',
            'sleep': '#007bff',
            'weight': '#6f42c1',
            'activity': '#fd7e14',
            'heart_rate': '#dc3545',
        }
        color = colors.get(obj.goal_type, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{}</span>',
                          color, obj.get_goal_type_display())
    goal_type_badge.short_description = 'Type'
    
    def progress_bar(self, obj):
        width = min(obj.progress_percentage, 100)
        color = '#28a745' if obj.progress_percentage >= 100 else '#007bff'
        return format_html(
            '<div style="width: 100px; height: 20px; background-color: #e9ecef; '
            'border-radius: 3px; overflow: hidden; position: relative;">'
            '<div style="width: {}%; height: 100%; background-color: {};">'
            '</div><span style="position: absolute; top: 0; left: 0; width: 100%; '
            'text-align: center; line-height: 20px; font-size: 12px; color: #000;">'
            '{:.1f}%</span></div>',
            width, color, obj.progress_percentage
        )
    progress_bar.short_description = 'Progress'
    
    def progress_bar_display(self, obj):
        return self.progress_bar(obj)
    progress_bar_display.short_description = 'Progress'
    
    def target_display(self, obj):
        return f"{obj.current_value:.1f}/{obj.target_value:.1f} {obj.unit}"
    target_display.short_description = 'Progress'
    
    def status_badge(self, obj):
        if obj.is_completed:
            return format_html('<span style="background-color: #28a745; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">✓ Completed</span>')
        elif obj.is_active:
            return format_html('<span style="background-color: #007bff; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">Active</span>')
        return format_html('<span style="background-color: #6c757d; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">Inactive</span>')
    status_badge.short_description = 'Status'
    
    def days_remaining_display(self, obj):
        if obj.end_date:
            today = timezone.now().date()
            days = (obj.end_date - today).days
            color = '#dc3545' if days < 7 else '#ffc107' if days < 30 else '#28a745'
            return format_html('<span style="color: {}; font-weight: bold;">{} days</span>',
                              color, max(days, 0))
        return "No end date"
    days_remaining_display.short_description = 'Days Remaining'
    
    def streak_display(self, obj):
        return f"Current: {obj.current_streak} days, Longest: {obj.longest_streak} days"
    streak_display.short_description = 'Streaks'
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(is_completed=True, completed_at=timezone.now())
        self.message_user(request, f'{updated} goals marked as completed.')
    mark_completed.short_description = "Mark selected as completed"
    
    def mark_incomplete(self, request, queryset):
        updated = queryset.update(is_completed=False, completed_at=None)
        self.message_user(request, f'{updated} goals marked as incomplete.')
    mark_incomplete.short_description = "Mark selected as incomplete"
    
    def activate_goals(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} goals activated.')
    activate_goals.short_description = "Activate selected goals"
    
    def deactivate_goals(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} goals deactivated.')
    deactivate_goals.short_description = "Deactivate selected goals"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(HealthAlert)
class HealthAlertAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'severity_badge', 'alert_type_display', 
                    'title_short', 'status_badge', 'time_since')
    list_filter = ('alert_type', 'severity', 'is_read', 'is_acknowledged', 
                   DateRangeFilter, 'user')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('created_at', 'read_at', 'acknowledged_at', 
                      'time_since_display', 'details_summary')
    list_per_page = 50
    date_hierarchy = 'triggered_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('user', 'alert_type', 'severity', 'title', 'message')
        }),
        ('Metrics', {
            'fields': ('metric_value', 'metric_unit', 'threshold_value')
        }),
        ('Status', {
            'fields': ('is_read', 'is_acknowledged', 'time_since_display')
        }),
        ('Details', {
            'fields': ('details_summary', 'sent_via_push', 'sent_via_email', 'sent_via_sms'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'acknowledge_alerts', 
               'escalate_severity', 'dismiss_alerts']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def severity_badge(self, obj):
        colors = {
            'critical': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#28a745',
            'info': '#17a2b8'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{}</span>',
                          color, obj.get_severity_display().upper())
    severity_badge.short_description = 'Severity'
    
    def alert_type_display(self, obj):
        return obj.get_alert_type_display()
    alert_type_display.short_description = 'Type'
    
    def title_short(self, obj):
        return obj.title[:40] + '...' if len(obj.title) > 40 else obj.title
    title_short.short_description = 'Title'
    
    def status_badge(self, obj):
        if obj.is_acknowledged:
            return format_html('<span style="background-color: #28a745; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">Acknowledged</span>')
        elif obj.is_read:
            return format_html('<span style="background-color: #6c757d; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">Read</span>')
        return format_html('<span style="background-color: #dc3545; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">Unread</span>')
    status_badge.short_description = 'Status'
    
    def time_since(self, obj):
        delta = timezone.now() - obj.triggered_at
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        return "Just now"
    time_since.short_description = 'Time'
    
    def time_since_display(self, obj):
        return self.time_since(obj)
    time_since_display.short_description = 'Triggered'
    
    def details_summary(self, obj):
        details = []
        if obj.metric_value:
            details.append(f"Value: {obj.metric_value} {obj.metric_unit}")
        if obj.threshold_value:
            details.append(f"Threshold: {obj.threshold_value}")
        
        return ', '.join(details) if details else "No additional details"
    details_summary.short_description = 'Alert Details'
    
    def escalate_severity(self, request, queryset):
        # Map current severity to next level
        severity_map = {
            'info': 'low',
            'low': 'medium',
            'medium': 'high',
            'high': 'critical'
        }
        
        updated = 0
        for alert in queryset:
            if alert.severity in severity_map:
                alert.severity = severity_map[alert.severity]
                alert.save()
                updated += 1
        
        self.message_user(request, f'{updated} alerts escalated.')
    escalate_severity.short_description = "Escalate severity"
    
    def dismiss_alerts(self, request, queryset):
        updated = queryset.update(is_read=True, is_acknowledged=True, 
                                 read_at=timezone.now(), acknowledged_at=timezone.now())
        self.message_user(request, f'{updated} alerts dismissed.')
    dismiss_alerts.short_description = "Dismiss alerts"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(HealthInsight)
class HealthInsightAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'category_badge', 'insight_type_display', 
                    'title_short', 'confidence_badge', 'status_badge', 'age_display')
    list_filter = ('insight_type', 'category', 'is_new', 'is_applied', 
                   'is_dismissed', 'generated_by', DateRangeFilter, 'user')
    search_fields = ('user__email', 'title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'data_preview', 
                      'visualization_preview', 'age_details')
    list_per_page = 30
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'insight_type', 'category', 'title', 'description')
        }),
        ('Confidence & Data', {
            'fields': ('confidence', 'data_preview', 'visualization_preview')
        }),
        ('Time Period', {
            'fields': ('start_date', 'end_date', 'age_details')
        }),
        ('Actions', {
            'fields': ('action_items', 'recommendations'),
            'classes': ('wide',)
        }),
        ('Status', {
            'fields': ('is_new', 'is_applied', 'is_dismissed')
        }),
        ('Metadata', {
            'fields': ('generated_by', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'apply_insights', 
               'dismiss_insights', 'regenerate_insights']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def category_badge(self, obj):
        colors = {
            'activity': '#28a745',
            'sleep': '#007bff',
            'heart': '#dc3545',
            'nutrition': '#fd7e14',
            'stress': '#6f42c1',
            'recovery': '#17a2b8',
            'overall': '#6c757d'
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{}</span>',
                          color, obj.get_category_display())
    category_badge.short_description = 'Category'
    
    def insight_type_display(self, obj):
        return obj.get_insight_type_display()
    insight_type_display.short_description = 'Type'
    
    def title_short(self, obj):
        return obj.title[:40] + '...' if len(obj.title) > 40 else obj.title
    title_short.short_description = 'Title'
    
    def confidence_badge(self, obj):
        color = '#dc3545'  # red
        if obj.confidence >= 0.9:
            color = '#28a745'  # green
        elif obj.confidence >= 0.7:
            color = '#ffc107'  # yellow
        
        return format_html('<span style="background-color: {}; color: white; '
                          'padding: 2px 6px; border-radius: 3px;">{:.0%}</span>',
                          color, obj.confidence)
    confidence_badge.short_description = 'Confidence'
    
    def status_badge(self, obj):
        if obj.is_applied:
            return format_html('<span style="background-color: #28a745; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">Applied</span>')
        elif obj.is_dismissed:
            return format_html('<span style="background-color: #6c757d; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">Dismissed</span>')
        elif obj.is_new:
            return format_html('<span style="background-color: #007bff; color: white; '
                              'padding: 2px 6px; border-radius: 3px;">New</span>')
        return format_html('<span style="background-color: #ffc107; color: #000; '
                          'padding: 2px 6px; border-radius: 3px;">Pending</span>')
    status_badge.short_description = 'Status'
    
    def age_display(self, obj):
        return f"{obj.age_days}d"
    age_display.short_description = 'Age'
    
    def data_preview(self, obj):
        if obj.data_points:
            # Truncate for display
            preview = json.dumps(obj.data_points, indent=2)[:500]
            if len(json.dumps(obj.data_points)) > 500:
                preview += "..."
            return format_html('<pre style="max-height: 200px; overflow: auto; '
                              'background-color: #f8f9fa; padding: 10px; '
                              'border-radius: 3px;">{}</pre>', preview)
        return "No data points"
    data_preview.short_description = 'Data Points'
    
    def visualization_preview(self, obj):
        if obj.visualization_data:
            preview = json.dumps(obj.visualization_data, indent=2)[:300]
            if len(json.dumps(obj.visualization_data)) > 300:
                preview += "..."
            return format_html('<pre style="max-height: 150px; overflow: auto; '
                              'background-color: #f8f9fa; padding: 10px; '
                              'border-radius: 3px; font-size: 12px;">{}</pre>', preview)
        return "No visualization data"
    visualization_preview.short_description = 'Visualization Data'
    
    def age_details(self, obj):
        return f"Generated {obj.age_days} days ago"
    age_details.short_description = 'Age'
    
    def regenerate_insights(self, request, queryset):
        # In a real application, this would call your insight generation service
        # For now, just mark as new to simulate regeneration
        updated = queryset.update(is_new=True, generated_at=timezone.now())
        self.message_user(request, f'{updated} insights marked for regeneration.')
    regenerate_insights.short_description = "Regenerate insights"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ============================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================

class HealthAdminSite(admin.AdminSite):
    site_header = "Health Monitoring Platform Admin"
    site_title = "Health Monitoring Platform"
    index_title = "Health Data Administration"
    
    def get_app_list(self, request, app_label=None):
        """
        Customize the app list to group health-related models
        """
        app_list = super().get_app_list(request)
        
        # Find the health app and customize its models order
        for app in app_list:
            if app['app_label'] == 'health_data':  # Replace with your actual app name
                # Reorder models based on importance/frequency of use
                model_order = [
                    'DailySummary',
                    'HeartRateReading',
                    'SleepSession',
                    'Activity',
                    'HealthGoal',
                    'HealthAlert',
                    'HealthInsight'
                ]
                
                # Sort models according to our preferred order
                app['models'].sort(key=lambda x: model_order.index(x['object_name']) 
                                  if x['object_name'] in model_order else 999)
                
                # Add description to each model
                model_descriptions = {
                    'DailySummary': 'Daily aggregated health metrics',
                    'HeartRateReading': 'Individual heart rate readings',
                    'SleepSession': 'Sleep sessions with detailed stages',
                    'Activity': 'Physical activities and workouts',
                    'HealthGoal': 'User health goals and targets',
                    'HealthAlert': 'Health alerts and notifications',
                    'HealthInsight': 'Generated health insights and patterns'
                }
                
                for model in app['models']:
                    if model['object_name'] in model_descriptions:
                        model['description'] = model_descriptions[model['object_name']]
        
        return app_list


# Register with default admin site (if you're not using custom AdminSite)
admin.site.site_header = "Health Monitoring Platform Admin"
admin.site.site_title = "Health Monitoring Platform"
admin.site.index_title = "Welcome to Health Monitoring Platform Administration"