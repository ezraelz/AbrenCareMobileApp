# devices/models.py
from django.db import models
from users.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class DeviceType(models.TextChoices):
    SMARTWATCH = 'smartwatch', 'Smart Watch'
    FITNESS_BAND = 'fitness_band', 'Fitness Band'
    PHONE = 'phone', 'Phone'
    SMART_SCALE = 'smart_scale', 'Smart Scale'
    HEART_RATE_MONITOR = 'heart_rate_monitor', 'Heart Rate Monitor'
    BLOOD_PRESSURE = 'blood_pressure', 'Blood Pressure Monitor'
    OTHER = 'other', 'Other'


class DeviceManufacturer(models.TextChoices):
    APPLE = 'apple', 'Apple'
    FITBIT = 'fitbit', 'Fitbit'
    GARMIN = 'garmin', 'Garmin'
    SAMSUNG = 'samsung', 'Samsung'
    XIAOMI = 'xiaomi', 'Xiaomi'
    HUAWEI = 'huawei', 'Huawei'
    AMAZFIT = 'amazfit', 'Amazfit'
    WITHINGS = 'withings', 'Withings'
    POLAR = 'polar', 'Polar'
    OTHER = 'other', 'Other'


class ConnectionType(models.TextChoices):
    BLUETOOTH = 'bluetooth', 'Bluetooth'
    WIFI = 'wifi', 'Wi-Fi'
    USB = 'usb', 'USB'
    CLOUD = 'cloud', 'Cloud API'


class DeviceStatus(models.TextChoices):
    DISCONNECTED = 'disconnected', 'Disconnected'
    CONNECTED = 'connected', 'Connected'
    SYNCING = 'syncing', 'Syncing'
    PAIRED = 'paired', 'Paired'
    ERROR = 'error', 'Error'
    LOW_BATTERY = 'low_battery', 'Low Battery'


class Device(models.Model):
    """Main device model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DeviceType.choices, default=DeviceType.SMARTWATCH)
    manufacturer = models.CharField(max_length=20, choices=DeviceManufacturer.choices, default=DeviceManufacturer.OTHER)
    model = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Connection information
    connection_type = models.CharField(max_length=20, choices=ConnectionType.choices, default=ConnectionType.BLUETOOTH)
    bluetooth_address = models.CharField(max_length=17, blank=True, null=True)  # Format: XX:XX:XX:XX:XX:XX
    bluetooth_name = models.CharField(max_length=100, blank=True, null=True)
    wifi_mac_address = models.CharField(max_length=17, blank=True, null=True)
    device_id = models.CharField(max_length=200, unique=True, blank=True, null=True)  # Unique device identifier
    
    # API credentials for cloud-based devices
    api_key = models.CharField(max_length=500, blank=True, null=True)
    api_secret = models.CharField(max_length=500, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Device status
    battery_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        blank=True,
        null=True
    )
    last_synced = models.DateTimeField(blank=True, null=True)
    last_connected = models.DateTimeField(blank=True, null=True)
    is_connected = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=DeviceStatus.choices, default=DeviceStatus.DISCONNECTED)
    
    # Device capabilities
    capabilities = models.JSONField(default=dict, blank=True)  # What data can it provide
    supported_metrics = models.JSONField(default=list, blank=True)  # List of metrics it can track
    
    # Device info
    firmware_version = models.CharField(max_length=50, blank=True, null=True)
    hardware_version = models.CharField(max_length=50, blank=True, null=True)
    software_version = models.CharField(max_length=50, blank=True, null=True)
    
    # Settings
    auto_sync = models.BooleanField(default=True)
    sync_frequency = models.IntegerField(default=15)  # minutes
    sync_on_startup = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_error = models.TextField(blank=True, null=True)
    error_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-last_synced', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_connected']),
            models.Index(fields=['bluetooth_address']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        return f"{self.device_name} ({self.manufacturer}) - {self.user.username}"
    
    def get_connection_info(self):
        """Get connection information based on connection type"""
        if self.connection_type == ConnectionType.BLUETOOTH:
            return {
                'type': 'bluetooth',
                'address': self.bluetooth_address,
                'name': self.bluetooth_name
            }
        elif self.connection_type == ConnectionType.WIFI:
            return {
                'type': 'wifi',
                'mac_address': self.wifi_mac_address
            }
        elif self.connection_type == ConnectionType.CLOUD:
            return {
                'type': 'cloud',
                'has_token': bool(self.access_token)
            }
        return {'type': self.connection_type}
    
    def update_status(self, status, save=True):
        """Update device status"""
        self.status = status
        if status == DeviceStatus.CONNECTED:
            self.last_connected = timezone.now()
            self.is_connected = True
        elif status == DeviceStatus.DISCONNECTED:
            self.is_connected = False
        if save:
            self.save()
    
    def can_sync(self):
        """Check if device can sync"""
        return (
            self.is_connected or 
            self.connection_type == ConnectionType.CLOUD
        ) and self.status != DeviceStatus.ERROR


class DeviceSyncLog(models.Model):
    """Log of device sync operations"""
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=20, choices=[
        ('manual', 'Manual'),
        ('auto', 'Auto'),
        ('scheduled', 'Scheduled'),
        ('background', 'Background')
    ])
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ])
    data_synced = models.JSONField(default=dict, blank=True)  # What data was synced
    metrics_count = models.JSONField(default=dict, blank=True)  # Count of each metric type
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.device.device_name} - {self.status} - {self.started_at}"


class DeviceConnectionLog(models.Model):
    """Log of device connection attempts"""
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='connection_logs')
    connection_type = models.CharField(max_length=20)
    attempted_at = models.DateTimeField()
    connected_at = models.DateTimeField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True, null=True)
    signal_strength = models.IntegerField(null=True, blank=True)  # For Bluetooth/WiFi
    battery_level = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-attempted_at']


class DeviceDataCache(models.Model):
    """Cache for device data to reduce API calls"""
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='data_cache')
    data_type = models.CharField(max_length=50)  # steps, heart_rate, sleep, etc.
    date = models.DateField()
    data = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ['device', 'data_type', 'date']
        indexes = [
            models.Index(fields=['device', 'data_type', 'date']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at


class DeviceDriver(models.Model):
    """Driver/plugin for different device manufacturers"""
    manufacturer = models.CharField(max_length=20, choices=DeviceManufacturer.choices)
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    driver_class = models.CharField(max_length=200)  # Python class path
    connection_types = models.JSONField(default=list)  # ['bluetooth', 'cloud', etc.]
    capabilities = models.JSONField(default=dict)  # What it can do
    config_schema = models.JSONField(default=dict)  # Configuration schema
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['manufacturer', 'version']
    
    def __str__(self):
        return f"{self.manufacturer} - {self.name} v{self.version}"
    
