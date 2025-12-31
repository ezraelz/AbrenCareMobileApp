import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from devices.models import Device

logger = logging.getLogger(__name__)


class GenericDeviceAPI:
    """Generic API integration for devices without specific integrations"""
    
    name = "Generic Device API"
    supports_oauth = False
    supports_api_key = True
    
    def __init__(self):
        self.base_url = ""
        self.timeout = 30
    
    def get_authorization_url(self, state: str = None, scope: List[str] = None) -> Optional[str]:
        """Get OAuth authorization URL (not supported for generic devices)"""
        return None
    
    def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Exchange authorization code for tokens (not supported)"""
        raise NotImplementedError("OAuth not supported for generic devices")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh OAuth tokens (not supported)"""
        raise NotImplementedError("Token refresh not supported for generic devices")
    
    def revoke_tokens(self, device: Device) -> bool:
        """Revoke device tokens (not applicable for generic devices)"""
        logger.info(f"No token revocation needed for generic device {device.id}")
        return True
    
    def get_device_info(self, device: Device) -> Dict[str, Any]:
        """Get device information from API"""
        try:
            if device.api_endpoint:
                # Try to fetch device info from the provided API endpoint
                headers = self._get_headers(device)
                response = requests.get(
                    f"{device.api_endpoint}/info",
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
            
            # Return basic info if API call fails or no endpoint
            return {
                'connected': device.is_connected,
                'model': device.device_type.name if device.device_type else 'Unknown',
                'firmware': device.firmware_version or 'Unknown',
                'battery_level': device.battery_level,
                'last_updated': device.last_battery_update
            }
            
        except Exception as e:
            logger.warning(f"Failed to get device info for generic device {device.id}: {e}")
            return {
                'connected': device.is_connected,
                'error': str(e)
            }
    
    def fetch_data(
        self, 
        device: Device, 
        date_range: Dict[str, datetime], 
        metrics: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch data from generic device API"""
        
        result = {
            'heart_rate': [],
            'sleep': [],
            'activity': [],
            'steps': []
        }
        
        try:
            if not device.api_endpoint:
                logger.warning(f"No API endpoint configured for device {device.id}")
                return result
            
            # Prepare request
            headers = self._get_headers(device)
            params = {
                'start_date': date_range['start'].isoformat(),
                'end_date': date_range['end'].isoformat(),
                'metrics': ','.join(metrics) if metrics else 'all'
            }
            
            # Make API call
            response = requests.get(
                f"{device.api_endpoint}/data",
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Map generic data to our expected format
                if 'heart_rate' in data:
                    result['heart_rate'] = self._process_heart_rate_data(data['heart_rate'])
                
                if 'sleep' in data:
                    result['sleep'] = self._process_sleep_data(data['sleep'])
                
                if 'activities' in data:
                    result['activity'] = self._process_activity_data(data['activities'])
                
                if 'steps' in data:
                    result['steps'] = self._process_step_data(data['steps'])
                
                logger.info(f"Fetched {sum(len(v) for v in result.values())} records from generic device {device.id}")
            else:
                logger.error(f"API request failed for device {device.id}: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching data from generic device {device.id}: {e}")
        except Exception as e:
            logger.error(f"Error fetching data from generic device {device.id}: {e}")
        
        return result
    
    def test_connection(self, device: Device) -> Dict[str, Any]:
        """Test connection to device API"""
        
        test_result = {
            'connected': False,
            'latency_ms': None,
            'error': None
        }
        
        try:
            if not device.api_endpoint:
                test_result['error'] = 'No API endpoint configured'
                return test_result
            
            import time
            start_time = time.time()
            
            headers = self._get_headers(device)
            response = requests.get(
                f"{device.api_endpoint}/ping",
                headers=headers,
                timeout=10
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                test_result.update({
                    'connected': True,
                    'latency_ms': round(latency_ms, 2),
                    'api_version': response.json().get('version', 'unknown')
                })
            else:
                test_result['error'] = f"API returned status {response.status_code}"
                
        except requests.exceptions.Timeout:
            test_result['error'] = 'Connection timeout'
        except requests.exceptions.ConnectionError:
            test_result['error'] = 'Connection refused'
        except Exception as e:
            test_result['error'] = str(e)
        
        return test_result
    
    def get_capabilities(self, device: Device) -> Dict[str, Any]:
        """Get device capabilities"""
        
        capabilities = {
            'metrics': [],
            'features': [],
            'limits': {}
        }
        
        try:
            if device.api_endpoint:
                headers = self._get_headers(device)
                response = requests.get(
                    f"{device.api_endpoint}/capabilities",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
            
            # Fallback to device type typical metrics
            if device.device_type and device.device_type.typical_metrics:
                capabilities['metrics'] = device.device_type.typical_metrics
            
            # Add basic features for generic devices
            capabilities['features'] = [
                'heart_rate_monitoring',
                'step_counting',
                'sleep_tracking',
                'activity_recognition'
            ]
            
            capabilities['limits'] = {
                'max_history_days': 90,
                'max_request_points': 1000,
                'supported_formats': ['json']
            }
            
        except Exception as e:
            logger.warning(f"Failed to get capabilities for generic device {device.id}: {e}")
        
        return capabilities
    
    def _get_headers(self, device: Device) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            'User-Agent': f'HealthMonitorApp/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if device.api_key:
            headers['Authorization'] = f'Bearer {device.api_key}'
        elif device.access_token:
            headers['Authorization'] = f'Bearer {device.access_token}'
        
        return headers
    
    def _process_heart_rate_data(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Process raw heart rate data into standardized format"""
        processed = []
        
        for record in data:
            try:
                processed_record = {
                    'bpm': int(record.get('value', record.get('bpm', 0))),
                    'timestamp': datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')),
                    'confidence': float(record.get('confidence', 1.0)),
                    'context': record.get('context', 'unknown')
                }
                
                # Validate heart rate range
                if 30 <= processed_record['bpm'] <= 250:
                    processed.append(processed_record)
                    
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping invalid heart rate record: {e}")
                continue
        
        return processed
    
    def _process_sleep_data(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Process raw sleep data into standardized format"""
        processed = []
        
        for record in data:
            try:
                processed_record = {
                    'start_time': datetime.fromisoformat(record['start_time'].replace('Z', '+00:00')),
                    'end_time': datetime.fromisoformat(record['end_time'].replace('Z', '+00:00')),
                    'duration_minutes': int(record.get('duration_minutes', 
                        (datetime.fromisoformat(record['end_time'].replace('Z', '+00:00')) - 
                         datetime.fromisoformat(record['start_time'].replace('Z', '+00:00'))).total_seconds() / 60)),
                    'awake_minutes': int(record.get('awake_minutes', 0)),
                    'light_minutes': int(record.get('light_minutes', 0)),
                    'deep_minutes': int(record.get('deep_minutes', 0)),
                    'rem_minutes': int(record.get('rem_minutes', 0)),
                    'quality_score': float(record.get('quality_score', 0)) if record.get('quality_score') else None
                }
                
                # Validate duration (max 24 hours)
                if 0 <= processed_record['duration_minutes'] <= 1440:
                    processed.append(processed_record)
                    
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping invalid sleep record: {e}")
                continue
        
        return processed
    
    def _process_activity_data(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Process raw activity data into standardized format"""
        processed = []
        
        for record in data:
            try:
                processed_record = {
                    'activity_type': record.get('type', 'other').lower(),
                    'start_time': datetime.fromisoformat(record['start_time'].replace('Z', '+00:00')),
                    'end_time': datetime.fromisoformat(record['end_time'].replace('Z', '+00:00')),
                    'duration_minutes': int(record.get('duration_minutes',
                        (datetime.fromisoformat(record['end_time'].replace('Z', '+00:00')) - 
                         datetime.fromisoformat(record['start_time'].replace('Z', '+00:00'))).total_seconds() / 60)),
                    'calories_burned': float(record.get('calories', 0)),
                    'distance_km': float(record.get('distance_km', 0)) if record.get('distance_km') else None,
                    'steps': int(record.get('steps', 0)) if record.get('steps') else None,
                    'avg_heart_rate': int(record.get('avg_heart_rate')) if record.get('avg_heart_rate') else None,
                    'max_heart_rate': int(record.get('max_heart_rate')) if record.get('max_heart_rate') else None
                }
                
                # Validate activity type
                valid_types = ['walking', 'running', 'cycling', 'swimming', 'workout', 'other']
                if processed_record['activity_type'] not in valid_types:
                    processed_record['activity_type'] = 'other'
                
                processed.append(processed_record)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping invalid activity record: {e}")
                continue
        
        return processed
    
    def _process_step_data(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Process raw step data into standardized format"""
        processed = []
        
        for record in data:
            try:
                processed_record = {
                    'timestamp': datetime.fromisoformat(record['date'].replace('Z', '+00:00')),
                    'steps': int(record['steps']),
                    'distance_meters': float(record.get('distance', 0)) * 1000 if record.get('distance') else None,
                    'calories': float(record.get('calories', 0)) if record.get('calories') else None
                }
                
                if processed_record['steps'] >= 0:
                    processed.append(processed_record)
                    
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping invalid step record: {e}")
                continue
        
        return processed
    