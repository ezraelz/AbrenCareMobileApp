from django.db import models


class DailySummary(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    date = models.DateField()
    avg_heart_rate = models.FloatField(null=True)
    total_steps = models.IntegerField(default=0)
    sleep_hours = models.FloatField(default=0)

