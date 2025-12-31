from django.urls import path
from .views import (
    DeviceWebhookView  
)
urlpatterns = [
    path('webhook/', DeviceWebhookView.as_view(), name='device-webhook'),
]
