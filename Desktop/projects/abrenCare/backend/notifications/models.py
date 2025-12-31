from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('health_alert', 'Health Alert'),
        ('goal_achieved', 'Goal Achieved'),
        ('reminder', 'Reminder'),
        ('system', 'System'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional related data
    related_model = models.CharField(max_length=50, blank=True)
    related_id = models.CharField(max_length=100, blank=True)
    
    # Delivery status
    is_read = models.BooleanField(default=False)
    sent_via_push = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']