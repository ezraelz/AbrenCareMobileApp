# devices/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Device, DeviceSyncLog, DeviceConnectionLog, 
    DeviceDataCache, DeviceDriver,
    DeviceType, DeviceManufacturer, ConnectionType, DeviceStatus
)
from users.serializers import UserSerializer


class DeviceSerializer(serializers.ModelSerializer):
    """Main device serializer"""
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=User.objects.all(),
        write_only=True
    )
    
    # Readable choices fields
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    manufacturer_display = serializers.CharField(source='get_manufacturer_display', read_only=True)
    connection_type_display = serializers.CharField(source='get_connection_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Connection info computed field
    connection_info = serializers.SerializerMethodField()
    
    # Security fields (write-only for sensitive data)
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    refresh_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Computed fields
    can_sync = serializers.BooleanField(read_only=True)
    is_online = serializers.SerializerMethodField()
    last_synced_display = serializers.SerializerMethodField()
    last_connected_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = [
            'id',
            'user', 'user_id',
            'device_name', 'device_type', 'device_type_display',
            'manufacturer', 'manufacturer_display',
            'model', 'serial_number',
            
            # Connection fields
            'connection_type', 'connection_type_display',
            'bluetooth_address', 'bluetooth_name',
            'wifi_mac_address', 'device_id',
            
            # Security fields (write-only)
            'api_key', 'api_secret', 'access_token', 'refresh_token',
            'token_expires_at',
            
            # Status fields
            'battery_level', 'last_synced', 'last_synced_display',
            'last_connected', 'last_connected_display',
            'is_connected', 'is_online',
            'status', 'status_display',
            
            # Capabilities
            'capabilities', 'supported_metrics',
            
            # Device info
            'firmware_version', 'hardware_version', 'software_version',
            
            # Settings
            'auto_sync', 'sync_frequency', 'sync_on_startup',
            
            # Computed fields
            'connection_info', 'can_sync',
            
            # Metadata
            'created_at', 'updated_at',
            'last_error', 'error_count',
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_error', 'error_count',
            'last_synced', 'last_connected', 'is_connected', 'status'
        ]
    
    def get_connection_info(self, obj):
        return obj.get_connection_info()
    
    def get_is_online(self, obj):
        """Check if device is online (connected or recently connected)"""
        if obj.is_connected:
            return True
        
        # For cloud devices, check token expiry
        if obj.connection_type == ConnectionType.CLOUD:
            if obj.token_expires_at:
                return obj.token_expires_at > timezone.now()
            return bool(obj.access_token)
        
        # For disconnected devices, check if they were recently connected
        if obj.last_connected:
            time_since_last = timezone.now() - obj.last_connected
            return time_since_last.total_seconds() < 300  # 5 minutes
        
        return False
    
    def get_last_synced_display(self, obj):
        if not obj.last_synced:
            return "Never"
        time_diff = timezone.now() - obj.last_synced
        if time_diff.days > 0:
            return f"{time_diff.days}d ago"
        elif time_diff.seconds > 3600:
            return f"{time_diff.seconds // 3600}h ago"
        elif time_diff.seconds > 60:
            return f"{time_diff.seconds // 60}m ago"
        return "Just now"
    
    def get_last_connected_display(self, obj):
        if not obj.last_connected:
            return "Never"
        time_diff = timezone.now() - obj.last_connected
        if time_diff.days > 0:
            return f"{time_diff.days}d ago"
        elif time_diff.seconds > 3600:
            return f"{time_diff.seconds // 3600}h ago"
        elif time_diff.seconds > 60:
            return f"{time_diff.seconds // 60}m ago"
        return "Just now"
    
    def validate(self, data):
        """Validate device data"""
        # Validate connection type specific fields
        connection_type = data.get('connection_type')
        
        if connection_type == ConnectionType.BLUETOOTH:
            if not data.get('bluetooth_address'):
                raise serializers.ValidationError({
                    'bluetooth_address': 'Bluetooth address is required for Bluetooth devices'
                })
        elif connection_type == ConnectionType.WIFI:
            if not data.get('wifi_mac_address'):
                raise serializers.ValidationError({
                    'wifi_mac_address': 'Wi-Fi MAC address is required for Wi-Fi devices'
                })
        elif connection_type == ConnectionType.CLOUD:
            if not data.get('api_key') or not data.get('api_secret'):
                # Only validate for new devices, existing ones might have tokens
                if self.instance is None:
                    raise serializers.ValidationError({
                        'api_key': 'API key is required for cloud devices',
                        'api_secret': 'API secret is required for cloud devices'
                    })
        
        # Validate battery level
        battery_level = data.get('battery_level')
        if battery_level is not None:
            if not 0 <= battery_level <= 100:
                raise serializers.ValidationError({
                    'battery_level': 'Battery level must be between 0 and 100'
                })
        
        # Validate sync frequency
        sync_frequency = data.get('sync_frequency')
        if sync_frequency is not None and sync_frequency < 1:
            raise serializers.ValidationError({
                'sync_frequency': 'Sync frequency must be at least 1 minute'
            })
        
        return data
    
    def create(self, validated_data):
        """Create device with default capabilities based on type"""
        device_type = validated_data.get('device_type')
        manufacturer = validated_data.get('manufacturer')
        
        # Set default capabilities based on device type
        if 'capabilities' not in validated_data:
            validated_data['capabilities'] = self.get_default_capabilities(device_type, manufacturer)
        
        # Set default supported metrics
        if 'supported_metrics' not in validated_data:
            validated_data['supported_metrics'] = self.get_default_metrics(device_type)
        
        return super().create(validated_data)
    
    def get_default_capabilities(self, device_type, manufacturer):
        """Get default capabilities for device type"""
        capabilities = {
            'can_sync': True,
            'can_notify': True,
            'supports_realtime': False,
        }
        
        if device_type == DeviceType.SMARTWATCH:
            capabilities.update({
                'can_track_steps': True,
                'can_track_heart_rate': True,
                'can_track_sleep': True,
                'supports_notifications': True,
                'supports_watch_faces': True,
            })
        elif device_type == DeviceType.FITNESS_BAND:
            capabilities.update({
                'can_track_steps': True,
                'can_track_heart_rate': True,
                'can_track_sleep': True,
                'supports_notifications': True,
            })
        elif device_type == DeviceType.HEART_RATE_MONITOR:
            capabilities.update({
                'can_track_heart_rate': True,
                'supports_realtime': True,
            })
        elif device_type == DeviceType.BLOOD_PRESSURE:
            capabilities.update({
                'can_track_blood_pressure': True,
            })
        elif device_type == DeviceType.SMART_SCALE:
            capabilities.update({
                'can_track_weight': True,
                'can_track_body_fat': True,
                'can_track_bmi': True,
            })
        
        return capabilities
    
    def get_default_metrics(self, device_type):
        """Get default metrics for device type"""
        metrics_map = {
            DeviceType.SMARTWATCH: ['steps', 'heart_rate', 'sleep', 'calories', 'distance'],
            DeviceType.FITNESS_BAND: ['steps', 'heart_rate', 'sleep', 'calories'],
            DeviceType.HEART_RATE_MONITOR: ['heart_rate'],
            DeviceType.BLOOD_PRESSURE: ['systolic', 'diastolic', 'pulse'],
            DeviceType.SMART_SCALE: ['weight', 'body_fat', 'bmi', 'muscle_mass'],
            DeviceType.PHONE: ['steps', 'location', 'screen_time'],
        }
        return metrics_map.get(device_type, [])


class DeviceCreateSerializer(DeviceSerializer):
    """Serializer for creating devices (simplified)"""
    class Meta(DeviceSerializer.Meta):
        fields = [
            'user_id',
            'device_name', 'device_type', 'manufacturer',
            'model', 'serial_number',
            'connection_type',
            'bluetooth_address', 'bluetooth_name',
            'wifi_mac_address', 'device_id',
            'api_key', 'api_secret',
            'auto_sync', 'sync_frequency',
        ]


class DeviceUpdateSerializer(DeviceSerializer):
    """Serializer for updating devices"""
    class Meta(DeviceSerializer.Meta):
        read_only_fields = DeviceSerializer.Meta.read_only_fields + [
            'user', 'user_id', 'device_type', 'manufacturer',
            'connection_type', 'device_id'
        ]


class DeviceStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating device status"""
    class Meta:
        model = Device
        fields = ['battery_level', 'status', 'is_connected', 'firmware_version']
    
    def update(self, instance, validated_data):
        # Update status and track connection time
        if 'status' in validated_data:
            new_status = validated_data['status']
            if new_status == DeviceStatus.CONNECTED:
                instance.last_connected = timezone.now()
                instance.is_connected = True
            elif new_status == DeviceStatus.DISCONNECTED:
                instance.is_connected = False
        
        return super().update(instance, validated_data)


class DeviceSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for device sync logs"""
    device = serializers.StringRelatedField(read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(
        source='device',
        queryset=Device.objects.all(),
        write_only=True
    )
    
    # Duration in human readable format
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceSyncLog
        fields = [
            'id', 'device', 'device_id',
            'sync_type', 'started_at', 'completed_at',
            'duration_seconds', 'duration_display',
            'status', 'data_synced', 'metrics_count',
            'error_message', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_duration_display(self, obj):
        if not obj.duration_seconds:
            return None
        
        seconds = obj.duration_seconds
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.2f}h"


class DeviceConnectionLogSerializer(serializers.ModelSerializer):
    """Serializer for device connection logs"""
    device = serializers.StringRelatedField(read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(
        source='device',
        queryset=Device.objects.all(),
        write_only=True
    )
    
    # Connection duration
    connection_duration = serializers.SerializerMethodField()
    
    # Signal strength indicator
    signal_strength_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceConnectionLog
        fields = [
            'id', 'device', 'device_id',
            'connection_type', 'attempted_at',
            'connected_at', 'disconnected_at',
            'connection_duration',
            'status', 'error_message',
            'signal_strength', 'signal_strength_display',
            'battery_level', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_connection_duration(self, obj):
        if not obj.connected_at or not obj.disconnected_at:
            return None
        
        duration = obj.disconnected_at - obj.connected_at
        seconds = duration.total_seconds()
        
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def get_signal_strength_display(self, obj):
        if obj.signal_strength is None:
            return None
        
        if obj.signal_strength >= 80:
            return "Excellent"
        elif obj.signal_strength >= 60:
            return "Good"
        elif obj.signal_strength >= 40:
            return "Fair"
        elif obj.signal_strength >= 20:
            return "Poor"
        else:
            return "Very Poor"


class DeviceDataCacheSerializer(serializers.ModelSerializer):
    """Serializer for device data cache"""
    device = serializers.StringRelatedField(read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(
        source='device',
        queryset=Device.objects.all(),
        write_only=True
    )
    
    # Cache status
    is_expired = serializers.BooleanField(read_only=True)
    will_expire_in = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceDataCache
        fields = [
            'id', 'device', 'device_id',
            'data_type', 'date', 'data',
            'last_updated', 'expires_at',
            'is_expired', 'will_expire_in'
        ]
        read_only_fields = ['last_updated']
    
    def get_will_expire_in(self, obj):
        if not obj.expires_at:
            return None
        
        time_until = obj.expires_at - timezone.now()
        seconds = time_until.total_seconds()
        
        if seconds <= 0:
            return "Expired"
        elif seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.0f}h"
        else:
            days = seconds / 86400
            return f"{days:.0f}d"


class DeviceDriverSerializer(serializers.ModelSerializer):
    """Serializer for device drivers"""
    manufacturer_display = serializers.CharField(source='get_manufacturer_display', read_only=True)
    
    class Meta:
        model = DeviceDriver
        fields = [
            'id', 'manufacturer', 'manufacturer_display',
            'name', 'version', 'driver_class',
            'connection_types', 'capabilities',
            'config_schema', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']


class DeviceWithLogsSerializer(DeviceSerializer):
    """Device serializer with related logs"""
    recent_sync_logs = DeviceSyncLogSerializer(many=True, read_only=True)
    recent_connection_logs = DeviceConnectionLogSerializer(many=True, read_only=True)
    
    class Meta(DeviceSerializer.Meta):
        fields = DeviceSerializer.Meta.fields + ['recent_sync_logs', 'recent_connection_logs']


class DeviceSimpleSerializer(serializers.ModelSerializer):
    """Simplified device serializer for lists"""
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    manufacturer_display = serializers.CharField(source='get_manufacturer_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'device_name',
            'device_type', 'device_type_display',
            'manufacturer', 'manufacturer_display',
            'model', 'connection_type',
            'battery_level', 'is_connected',
            'status', 'status_display',
            'last_synced', 'created_at'
        ]


class DeviceBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk device updates"""
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    auto_sync = serializers.BooleanField(required=False)
    sync_frequency = serializers.IntegerField(required=False, min_value=1)
    
    def validate_device_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one device ID is required")
        
        # Check if all devices exist
        existing_ids = Device.objects.filter(id__in=value).values_list('id', flat=True)
        non_existing = set(value) - set(existing_ids)
        
        if non_existing:
            raise serializers.ValidationError(
                f"Devices not found: {list(non_existing)}"
            )
        
        return value


class DeviceConnectionRequestSerializer(serializers.Serializer):
    """Serializer for device connection requests"""
    device_id = serializers.CharField(required=True)
    connection_type = serializers.ChoiceField(
        choices=ConnectionType.choices,
        required=True
    )
    
    # Bluetooth specific
    bluetooth_address = serializers.CharField(required=False, allow_blank=True)
    
    # Cloud specific
    api_key = serializers.CharField(required=False, allow_blank=True)
    api_secret = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        connection_type = data.get('connection_type')
        
        if connection_type == ConnectionType.BLUETOOTH:
            if not data.get('bluetooth_address'):
                raise serializers.ValidationError({
                    'bluetooth_address': 'Bluetooth address is required for Bluetooth connection'
                })
        
        elif connection_type == ConnectionType.CLOUD:
            if not data.get('api_key') or not data.get('api_secret'):
                raise serializers.ValidationError({
                    'api_key': 'API key is required for cloud connection',
                    'api_secret': 'API secret is required for cloud connection'
                })
        
        return data


class DeviceSyncRequestSerializer(serializers.Serializer):
    """Serializer for device sync requests"""
    sync_type = serializers.ChoiceField(
        choices=[('manual', 'Manual'), ('auto', 'Auto')],
        default='manual'
    )
    force = serializers.BooleanField(default=False)
    data_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


# Export all serializers
__all__ = [
    'DeviceSerializer',
    'DeviceCreateSerializer',
    'DeviceUpdateSerializer',
    'DeviceStatusUpdateSerializer',
    'DeviceSyncLogSerializer',
    'DeviceConnectionLogSerializer',
    'DeviceDataCacheSerializer',
    'DeviceDriverSerializer',
    'DeviceWithLogsSerializer',
    'DeviceSimpleSerializer',
    'DeviceBulkUpdateSerializer',
    'DeviceConnectionRequestSerializer',
    'DeviceSyncRequestSerializer',
]