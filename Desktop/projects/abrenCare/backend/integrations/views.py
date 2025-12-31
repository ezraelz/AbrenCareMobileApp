from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from devices.models import Device
from health_data.models import HealthInsight

# devices/views.py (update your webhook view)
import hmac
import hashlib
from django.conf import settings
from rest_framework import status

class DeviceWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # Verify webhook signature (if provided by device)
        signature = request.headers.get('X-Device-Signature')
        if signature:
            # Verify the signature
            expected_signature = hmac.new(
                key=settings.WEBHOOK_SECRET.encode(),
                msg=request.body,
                digestmod=hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)
        
        payload = request.data
        device_uid = payload.get("device_uid")
        metrics = payload.get("metrics", [])

        try:
            device = Device.objects.get(device_uid=device_uid, is_verified=True)
        except Device.DoesNotExist:
            return Response({"error": "Device not registered"}, status=400)

        for metric in metrics:
            HealthInsight.objects.create(
                user=device.user,
                device=device,
                metric_type=metric["type"],
                value=metric["value"],
                recorded_at=metric["timestamp"],
            )

        device.last_sync = timezone.now()
        device.status = "connected"
        device.save()

        return Response({"status": "Data ingested"})
    
