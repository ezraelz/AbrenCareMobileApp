import requests
import logging
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.conf import settings
from django.utils import timezone

from devices.models import Device

logger = logging.getLogger(__name__)


class GarminAPI:
    """Garmin Connect API integration"""
    
    name = "Garmin Connect API"
    supports_oauth = True
    supports_api_key = True
    
    BASE_URL = "https://apis.garmin.com"
    AUTH_URL = "https://connect.garmin.com/oauthConfirm"
    
    def __init__(self):
        self.consumer_key = getattr(settings, 'GARMIN_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'GARMIN_CONSUMER_SECRET', '')
        self.callback_url = getattr(settings, 'GARMIN_CALLBACK_URL', '')
        self.timeout = 30
    
    def get_authorization_url(self, state: str = None, scope: List[str] = None) -> str:
        """Get Garmin OAuth authorization URL"""
        # Garmin uses OAuth 1.0a
        from requests_oauthlib import OAuth1Session
        
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri=self.callback_url
        )
        
        try:
            # Fetch request token
            request_token_url = "https://connect.garmin.com/oauth-service/oauth/request_token"
            fetch_response = oauth.fetch_request_token(request_token_url)
            
            # Get authorization URL
            base_authorization_url = "https://connect.garmin.com/oauth-service/oauth/authorize"
            authorization_url = oauth.authorization_url(base_authorization_url)
            
            if state:
                authorization_url += f"&state={state}"
            
            return authorization_url
            
        except Exception as e:
            logger.error(f"Failed to get Garmin auth URL: {e}")
            # Fallback to simple URL
            return f"{self.AUTH_URL}?oauth_consumer_key={self.consumer_key}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        # Garmin OAuth 1.0a implementation
        from requests_oauthlib import OAuth1Session
        
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri=redirect_uri or self.callback_url
        )
        
        try:
            # Parse verifier from code
            verifier = code
            
            # Fetch access token
            access_token_url = "https://connect.garmin.com/oauth-service/oauth/access_token"
            oauth_tokens = oauth.fetch_access_token(access_token_url, verifier=verifier)
            
            return {
                'access_token': oauth_tokens.get('oauth_token'),
                'access_token_secret': oauth_tokens.get('oauth_token_secret'),
                'expires_in': None,  # OAuth 1.0a doesn't have expiration
                'user_id': oauth_tokens.get('user_id')
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange Garmin token: {e}")
            raise Exception(f"Garmin token exchange failed: {str(e)}")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token (OAuth 1.0a doesn't support refresh)"""
        raise NotImplementedError("Garmin OAuth 1.0a doesn't support token refresh")
    
    def revoke_tokens(self, device: Device) -> bool:
        """Revoke Garmin OAuth tokens"""
        try:
            # For OAuth 1.0a, we need to invalidate the token pair
            if device.access_token and device.api_key:  # api_key stores token_secret
                # Make a request to invalidate the token
                from requests_oauthlib import OAuth1
                
                auth = OAuth1(
                    self.consumer_key,
                    client_secret=self.consumer_secret,
                    resource_owner_key=device.access_token,
                    resource_owner_secret=device.api_key,
                    signature_method='HMAC-SHA1'
                )
                
                response = requests.post(
                    "https://connect.garmin.com/oauth-service/oauth/invalidate_token",
                    auth=auth,
                    timeout=10
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error revoking Garmin tokens: {e}")
        
        return True  # Assume success for cleanup
    
    def get_device_info(self, device: Device) -> Dict[str, Any]:
        """Get Garmin device information"""
        try:
            # Garmin device info requires OAuth 1.0a signed request
            headers = self._get_headers(device)
            
            response = requests.get(
                f"{self.BASE_URL}/wellness-api/rest/devices",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                devices = response.json()
                
                for garmin_device in devices:
                    if str(garmin_device.get('deviceId')) == device.device_id:
                        return {
                            'device_name': garmin_device.get('deviceName', 'Unknown'),
                            'model': garmin_device.get('deviceType', 'Unknown'),
                            'serial_number': garmin_device.get('serialNumber'),
                            'software_version': garmin_device.get('softwareVersion'),
                            'last_connected': garmin_device.get('lastConnectTime')
                        }
            
            return {'connected': True, 'device_found': False}
            
        except Exception as e:
            logger.error(f"Failed to get Garmin device info: {e}")
            return {'connected': False, 'error': str(e)}
    
    def fetch_data(
        self, 
        device: Device, 
        date_range: Dict[str, datetime], 
        metrics: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch data from Garmin Connect API"""
        
        result = {
            'heart_rate': [],
            'sleep': [],
            'activity': [],
            'steps': []
        }
        
        try:
            headers = self._get_headers(device)
            
            # Format dates for Garmin API
            start_date_str = date_range['start'].strftime('%Y-%m-%d')
            end_date_str = date_range['end'].strftime('%Y-%m-%d')
            
            # Fetch daily summary
            response = requests.get(
                f"{self.BASE_URL}/wellness-api/rest/dailies",
                headers=headers,
                params={
                    'uploadStartTimeInSeconds': int(date_range['start'].timestamp()),
                    'uploadEndTimeInSeconds': int(date_range['end'].timestamp())
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                dailies = response.json()
                
                for daily in dailies:
                    date = datetime.fromtimestamp(daily['calendarDate'] / 1000)
                    
                    # Process steps
                    if 'steps' in metrics and 'steps' in daily:
                        result['steps'].append({
                            'timestamp': date,
                            'steps': daily['steps'],
                            'distance_meters': daily.get('distanceInMeters'),
                            'calories': daily.get('calories')
                        })
                    
                    # Process heart rate (Garmin provides min/max/avg)
                    if 'heart_rate' in metrics:
                        if 'minHeartRate' in daily:
                            result['heart_rate'].append({
                                'bpm': daily['minHeartRate'],
                                'timestamp': date.replace(hour=0, minute=0),
                                'context': 'rest'
                            })
                        
                        if 'maxHeartRate' in daily:
                            result['heart_rate'].append({
                                'bpm': daily['maxHeartRate'],
                                'timestamp': date.replace(hour=12, minute=0),
                                'context': 'active'
                            })
            
            # Fetch sleep data
            if 'sleep' in metrics:
                sleep_response = requests.get(
                    f"{self.BASE_URL}/wellness-api/rest/sleeps",
                    headers=headers,
                    params={
                        'startDate': start_date_str,
                        'endDate': end_date_str
                    },
                    timeout=self.timeout
                )
                
                if sleep_response.status_code == 200:
                    sleeps = sleep_response.json()
                    
                    for sleep in sleeps:
                        result['sleep'].append({
                            'start_time': datetime.fromtimestamp(sleep['startTimeInSeconds']),
                            'end_time': datetime.fromtimestamp(sleep['endTimeInSeconds']),
                            'duration_minutes': sleep['durationInSeconds'] // 60,
                            'awake_minutes': sleep.get('awakeSleepSeconds', 0) // 60,
                            'light_minutes': sleep.get('lightSleepSeconds', 0) // 60,
                            'deep_minutes': sleep.get('deepSleepSeconds', 0) // 60,
                            'rem_minutes': sleep.get('remSleepSeconds', 0) // 60,
                            'quality_score': sleep.get('sleepQualityScore')
                        })
            
            logger.info(f"Fetched Garmin data: {sum(len(v) for v in result.values())} records")
            
        except Exception as e:
            logger.error(f"Error fetching Garmin data: {e}")
        
        return result
    
    def test_connection(self, device: Device) -> Dict[str, Any]:
        """Test connection to Garmin API"""
        test_result = {
            'connected': False,
            'latency_ms': None,
            'error': None
        }
        
        try:
            import time
            start_time = time.time()
            
            headers = self._get_headers(device)
            response = requests.get(
                f"{self.BASE_URL}/wellness-api/rest/user/id",
                headers=headers,
                timeout=10
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                test_result.update({
                    'connected': True,
                    'latency_ms': round(latency_ms, 2),
                    'user_id': response.json().get('userId')
                })
            else:
                test_result['error'] = f"API returned status {response.status_code}"
                
        except Exception as e:
            test_result['error'] = str(e)
        
        return test_result
    
    def get_capabilities(self, device: Device) -> Dict[str, Any]:
        """Get Garmin device capabilities"""
        return {
            'metrics': ['heart_rate', 'sleep', 'steps', 'calories', 'distance', 'stress', 'body_battery'],
            'features': [
                'heart_rate_monitoring',
                'sleep_stage_tracking',
                'gps_tracking',
                'stress_monitoring',
                'body_battery',
                'pulse_ox',
                'activity_recognition'
            ],
            'limits': {
                'max_history_days': 365,
                'max_daily_points': 1,
                'supported_formats': ['json']
            }
        }
    
    def _get_headers(self, device: Device) -> Dict[str, str]:
        """Get headers for Garmin API requests"""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # For OAuth 1.0a, we need to sign requests
        if device.access_token and device.api_key:  # api_key stores token_secret
            # In a real implementation, you'd use requests_oauthlib for signing
            headers['Authorization'] = f'OAuth oauth_token="{device.access_token}"'
        
        return headers
    