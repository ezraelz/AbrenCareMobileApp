import importlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class IntegrationFactory:
    """Factory class to get the appropriate integration based on device type"""
    
    # Map device type names to integration classes
    INTEGRATION_MAP = {
        'fitbit': 'fitbit_api.FitbitAPI',
        'garmin': 'garmin_api.GarminAPI',
        'apple': 'apple_health.AppleHealthAPI',
        'apple_watch': 'apple_health.AppleHealthAPI',
        'samsung': 'samsung_health.SamsungHealthAPI',
        'huawei': 'huawei_health.HuaweiHealthAPI',
        'withings': 'withings_api.WithingsAPI',
        'polar': 'polar_api.PolarAPI',
        'suunto': 'suunto_api.SuuntoAPI',
    }
    
    @staticmethod
    def get_integration(device_type_name: str):
        """Get integration instance for device type"""
        device_type_lower = device_type_name.lower()
        
        # Find matching integration
        integration_key = None
        for key in IntegrationFactory.INTEGRATION_MAP.keys():
            if key in device_type_lower:
                integration_key = key
                break
        
        if not integration_key:
            # Try generic integration
            from .generic_api import GenericDeviceAPI
            return GenericDeviceAPI()
        
        # Import and instantiate the integration
        module_path, class_name = IntegrationFactory.INTEGRATION_MAP[integration_key].rsplit('.', 1)
        
        try:
            module = importlib.import_module(f'apps.devices.integrations.{module_path}')
            integration_class = getattr(module, class_name)
            return integration_class()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load integration {integration_key}: {e}")
            # Fallback to generic integration
            from .generic_api import GenericDeviceAPI
            return GenericDeviceAPI()
    
    @staticmethod
    def get_available_integrations():
        """Get list of available integrations"""
        return list(IntegrationFactory.INTEGRATION_MAP.keys())
    
    @staticmethod
    def is_integration_supported(device_type_name: str) -> bool:
        """Check if integration is supported for device type"""
        device_type_lower = device_type_name.lower()
        
        for key in IntegrationFactory.INTEGRATION_MAP.keys():
            if key in device_type_lower:
                return True
        
        return False