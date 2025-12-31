import requests
import base64
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.conf import settings
from django.utils import timezone

from devices.models import Device

logger = logging.getLogger(__name__)


class FitbitAPI:
    """Fitbit API integration"""
    
    name = "Fitbit API"
    supports_oauth = True
    supports_api_key = False
    
    BASE_URL = "https://api.fitbit.com"
    AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
    TOKEN_URL = "https://api.fitbit.com/oauth2/token"
    REVOKE_URL = "https://api.fitbit.com/oauth2/revoke"
    
    def __init__(self):
        self.client_id = getattr(settings, 'FITBIT_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'FITBIT_CLIENT_SECRET', '')
        self.redirect_uri = getattr(settings, 'FITBIT_REDIRECT_URI', '')
        self.timeout = 30
    
    def get_authorization_url(self, state: str = None, scope: List[str] = None) -> str:
        """Get Fitbit OAuth authorization URL"""
        scope_list = scope or ['activity', 'heartrate', 'sleep', 'profile']
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': ' '.join(scope_list),
            'redirect_uri': self.redirect_uri,
            'expires_in': '604800',  # 7 days
        }
        
        if state:
            params['state'] = state
        
        from urllib.parse import urlencode
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        redirect = redirect_uri or self.redirect_uri
        
        # Prepare authorization header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect,
            'code': code
        }
        
        response = requests.post(
            self.TOKEN_URL,
            headers=headers,
            data=data,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        token_data = response.json()
        
        return {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in': token_data['expires_in'],
            'scope': token_data['scope'],
            'user_id': token_data.get('user_id')
        }
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        response = requests.post(
            self.TOKEN_URL,
            headers=headers,
            data=data,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            error_msg = f"Token refresh failed: {response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        token_data = response.json()
        
        return {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in': token_data['expires_in']
        }
    
    def revoke_tokens(self, device: Device) -> bool:
        """Revoke Fitbit OAuth tokens"""
        if not device.access_token:
            return True
        
        try:
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_b64 = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'token': device.access_token,
                'token_type_hint': 'access_token'
            }
            
            response = requests.post(
                self.REVOKE_URL,
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully revoked Fitbit tokens for device {device.id}")
                return True
            else:
                logger.warning(f"Failed to revoke Fitbit tokens: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error revoking Fitbit tokens: {e}")
            return False
    
    def get_device_info(self, device: Device) -> Dict[str, Any]:
        """Get Fitbit device information"""
        try:
            headers = self._get_headers(device)
            
            # Get devices list
            response = requests.get(
                f"{self.BASE_URL}/1/user/-/devices.json",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                devices = response.json()
                
                # Find this specific device
                for fitbit_device in devices:
                    if fitbit_device.get('id') == device.device_id or fitbit_device.get('deviceVersion') in device.device_name:
                        return {
                            'device_name': fitbit_device.get('deviceVersion', 'Unknown'),
                            'model': fitbit_device.get('type', 'Unknown'),
                            'battery_level': fitbit_device.get('battery', 'Unknown'),
                            'battery_status': fitbit_device.get('batteryLevel', 'Unknown'),
                            'last_sync_time': fitbit_device.get('lastSyncTime'),
                            'mac_address': fitbit_device.get('mac')
                        }
            
            return {'connected': True, 'device_found': False}
            
        except Exception as e:
            logger.error(f"Failed to get Fitbit device info: {e}")
            return {'connected': False, 'error': str(e)}
    
    def fetch_data(
        self, 
        device: Device, 
        date_range: Dict[str, datetime], 
        metrics: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch data from Fitbit API"""
        
        result = {
            'heart_rate': [],
            'sleep': [],
            'activity': [],
            'steps': []
        }
        
        try:
            headers = self._get_headers(device)
            user_id = '-'
            
            # Format dates for Fitbit API
            start_date_str = date_range['start'].strftime('%Y-%m-%d')
            end_date_str = date_range['end'].strftime('%Y-%m-%d')
            
            # Fetch intraday heart rate if enabled
            if 'heart_rate' in metrics:
                heart_rate_data = self._fetch_heart_rate_data(
                    headers, user_id, start_date_str, end_date_str
                )
                result['heart_rate'] = heart_rate_data
            
            # Fetch sleep data if enabled
            if 'sleep' in metrics:
                sleep_data = self._fetch_sleep_data(
                    headers, user_id, start_date_str, end_date_str
                )
                result['sleep'] = sleep_data
            
            # Fetch activity data if enabled
            if any(m in metrics for m in ['activity', 'steps', 'calories']):
                activity_data = self._fetch_activity_data(
                    headers, user_id, start_date_str, end_date_str
                )
                result['activity'] = activity_data['activities']
                result['steps'] = activity_data['steps']
            
            logger.info(f"Fetched Fitbit data: {sum(len(v) for v in result.values())} records")
            
        except Exception as e:
            logger.error(f"Error fetching Fitbit data: {e}")
        
        return result
    
    def _fetch_heart_rate_data(self, headers: Dict, user_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch heart rate data from Fitbit"""
        heart_rate_data = []
        
        try:
            # Fetch daily summary first
            response = requests.get(
                f"{self.BASE_URL}/1/user/{user_id}/activities/heart/date/{start_date}/{end_date}.json",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Process daily summaries
                for day in data.get('activities-heart', []):
                    date = day['dateTime']
                    
                    # Get intraday data for each day
                    intraday_response = requests.get(
                        f"{self.BASE_URL}/1/user/{user_id}/activities/heart/date/{date}/1d/1min.json",
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    if intraday_response.status_code == 200:
                        intraday_data = intraday_response.json()
                        
                        for point in intraday_data['activities-heart-intraday']['dataset']:
                            timestamp_str = f"{date}T{point['time']}"
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            
                            heart_rate_data.append({
                                'bpm': point['value'],
                                'timestamp': timestamp,
                                'confidence': 1.0,
                                'context': 'rest'
                            })
        
        except Exception as e:
            logger.error(f"Error fetching Fitbit heart rate data: {e}")
        
        return heart_rate_data
    
    def _fetch_sleep_data(self, headers: Dict, user_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch sleep data from Fitbit"""
        sleep_data = []
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/1.2/user/{user_id}/sleep/date/{start_date}/{end_date}.json",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for sleep_log in data.get('sleep', []):
                    sleep_data.append({
                        'start_time': datetime.fromisoformat(sleep_log['startTime'].replace('Z', '+00:00')),
                        'end_time': datetime.fromisoformat(sleep_log['endTime'].replace('Z', '+00:00')),
                        'duration_minutes': sleep_log['duration'] // 60000,  # Convert ms to minutes
                        'awake_minutes': sleep_log.get('awakeCount', 0) * sleep_log.get('awakeDuration', 0) // 60000,
                        'light_minutes': sleep_log.get('levels', {}).get('summary', {}).get('light', {}).get('minutes', 0),
                        'deep_minutes': sleep_log.get('levels', {}).get('summary', {}).get('deep', {}).get('minutes', 0),
                        'rem_minutes': sleep_log.get('levels', {}).get('summary', {}).get('rem', {}).get('minutes', 0),
                        'quality_score': sleep_log.get('efficiency', 0),
                        'interruptions': sleep_log.get('awakeCount', 0)
                    })
        
        except Exception as e:
            logger.error(f"Error fetching Fitbit sleep data: {e}")
        
        return sleep_data
    
    def _fetch_activity_data(self, headers: Dict, user_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch activity data from Fitbit"""
        activities = []
        steps_data = []
        
        try:
            # Fetch activities list
            response = requests.get(
                f"{self.BASE_URL}/1/user/{user_id}/activities/list.json",
                headers=headers,
                params={
                    'afterDate': start_date,
                    'sort': 'asc',
                    'limit': 20
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for activity in data.get('activities', []):
                    activities.append({
                        'activity_type': activity.get('activityName', 'other').lower(),
                        'start_time': datetime.fromisoformat(activity['startTime'].replace('Z', '+00:00')),
                        'end_time': datetime.fromisoformat(activity['endTime'].replace('Z', '+00:00')),
                        'duration_minutes': activity.get('duration', 0) // 60000,
                        'calories_burned': activity.get('calories', 0),
                        'distance_km': activity.get('distance', 0),
                        'steps': activity.get('steps', 0)
                    })
            
            # Fetch steps data
            steps_response = requests.get(
                f"{self.BASE_URL}/1/user/{user_id}/activities/steps/date/{start_date}/{end_date}.json",
                headers=headers,
                timeout=self.timeout
            )
            
            if steps_response.status_code == 200:
                steps_json = steps_response.json()
                
                for day in steps_json['activities-steps']:
                    timestamp = datetime.fromisoformat(day['dateTime'].replace('Z', '+00:00'))
                    steps_data.append({
                        'timestamp': timestamp,
                        'steps': int(day['value'])
                    })
        
        except Exception as e:
            logger.error(f"Error fetching Fitbit activity data: {e}")
        
        return {
            'activities': activities,
            'steps': steps_data
        }
    
    def test_connection(self, device: Device) -> Dict[str, Any]:
        """Test connection to Fitbit API"""
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
                f"{self.BASE_URL}/1/user/-/profile.json",
                headers=headers,
                timeout=10
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                profile = response.json()
                test_result.update({
                    'connected': True,
                    'latency_ms': round(latency_ms, 2),
                    'user_id': profile['user']['encodedId'],
                    'display_name': profile['user']['displayName']
                })
            else:
                test_result['error'] = f"API returned status {response.status_code}"
                
        except Exception as e:
            test_result['error'] = str(e)
        
        return test_result
    
    def get_capabilities(self, device: Device) -> Dict[str, Any]:
        """Get Fitbit device capabilities"""
        return {
            'metrics': ['heart_rate', 'sleep', 'steps', 'calories', 'distance', 'active_minutes'],
            'features': [
                'heart_rate_monitoring',
                'sleep_stage_tracking',
                'gps_tracking',
                'calorie_tracking',
                'step_counting',
                'activity_recognition'
            ],
            'limits': {
                'max_history_days': 365,
                'max_intraday_points': 1440,
                'supported_formats': ['json']
            }
        }
    
    def _get_headers(self, device: Device) -> Dict[str, str]:
        """Get headers for Fitbit API requests"""
        return {
            'Authorization': f'Bearer {device.access_token}',
            'Accept': 'application/json',
            'Accept-Language': 'en_US'
        }
    