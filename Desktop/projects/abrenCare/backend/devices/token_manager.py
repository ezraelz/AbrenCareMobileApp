import logging
from datetime import timedelta
from django.utils import timezone
from typing import Optional, Dict, Any

from integrations.fitbit_api import FitbitAPI
from integrations.garmin_api import GarminAPI
from integrations.apple_health import AppleHealthAPI

logger = logging.getLogger(__name__)


class TokenManager:
    """Manage OAuth token lifecycle"""
    
    def refresh_token_if_needed(self, device) -> bool:
        """Refresh OAuth token if expired or about to expire"""
        
        if not device.access_token:
            return False
        
        # Check if token is expired or expires soon (within 5 minutes)
        if device.token_expiry and device.token_expiry > timezone.now() + timedelta(minutes=5):
            return True
        
        try:
            device_type_name = device.device_type.name.lower()
            
            if 'fitbit' in device_type_name:
                new_tokens = FitbitAPI.refresh_token(device.refresh_token)
            elif 'garmin' in device_type_name:
                new_tokens = GarminAPI.refresh_token(device.refresh_token)
            elif 'apple' in device_type_name:
                new_tokens = AppleHealthAPI.refresh_token(device.refresh_token)
            else:
                logger.warning(f"No token refresh implementation for {device_type_name}")
                return False
            
            # Update device with new tokens
            device.access_token = new_tokens['access_token']
            device.refresh_token = new_tokens.get('refresh_token', device.refresh_token)
            device.token_expiry = timezone.now() + timedelta(seconds=new_tokens['expires_in'])
            device.save()
            
            logger.info(f"Successfully refreshed tokens for device {device.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh tokens for device {device.id}: {e}")
            return False
    
    def revoke_tokens(self, device) -> bool:
        """Revoke OAuth tokens from provider"""
        
        if not device.access_token:
            return True
        
        try:
            device_type_name = device.device_type.name.lower()
            
            if 'fitbit' in device_type_name:
                success = FitbitAPI.revoke_tokens(device.access_token)
            elif 'garmin' in device_type_name:
                success = GarminAPI.revoke_tokens(device)
            elif 'apple' in device_type_name:
                success = AppleHealthAPI.revoke_tokens(device)
            else:
                logger.warning(f"No token revocation for {device_type_name}")
                success = True
            
            if success:
                logger.info(f"Successfully revoked tokens for device {device.id}")
            else:
                logger.warning(f"Failed to revoke tokens for device {device.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error revoking tokens for device {device.id}: {e}")
            return False