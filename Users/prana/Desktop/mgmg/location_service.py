#!/usr/bin/env python3
"""
Location detection service for country tracking
"""

import requests
import logging
from typing import Optional, Dict, Any
from flask import request

logger = logging.getLogger(__name__)

class LocationService:
    """Service to detect user's country based on IP address"""
    
    def __init__(self):
        # Use multiple IP geolocation services for reliability
        self.services = [
            {
                'name': 'ipapi',
                'url': 'http://ip-api.com/json/{ip}',
                'country_field': 'country'
            },
            {
                'name': 'ipinfo',
                'url': 'https://ipinfo.io/{ip}/json',
                'country_field': 'country'
            },
            {
                'name': 'ipgeolocation',
                'url': 'https://api.ipgeolocation.io/ipgeo?apiKey=free&ip={ip}',
                'country_field': 'country_name'
            }
        ]
    
    def get_client_ip(self, request_obj=None) -> str:
        """Extract real client IP from request"""
        if request_obj is None:
            try:
                request_obj = request
            except RuntimeError:
                # No request context
                return 'current'
        
        # Check for IP in various headers (for proxy/load balancer scenarios)
        possible_headers = [
            'X-Forwarded-For',
            'X-Real-IP', 
            'X-Client-IP',
            'CF-Connecting-IP',  # Cloudflare
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CF_CONNECTING_IP'
        ]
        
        for header in possible_headers:
            ip = request_obj.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one (client's real IP)
                ip_list = ip.split(',')
                for single_ip in ip_list:
                    single_ip = single_ip.strip()
                    # Skip private/local IPs and look for public IP
                    if not self._is_private_ip(single_ip):
                        logger.info(f"Found public IP in {header}: {single_ip}")
                        return single_ip
        
        # Fallback to remote_addr
        remote_ip = request_obj.remote_addr or 'current'
        logger.info(f"Using remote_addr: {remote_ip}")
        
        # If it's a private IP, detect current public IP
        if self._is_private_ip(remote_ip):
            logger.info(f"Private IP detected: {remote_ip}, will get public IP location")
            return 'current'
        
        return remote_ip
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/local"""
        if not ip or ip in ['127.0.0.1', 'localhost', '::1', 'unknown', 'current']:
            return True
        
        # Check for private IP ranges
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return True
                
            first = int(parts[0])
            second = int(parts[1])
            
            # Private IP ranges
            if first == 10:  # 10.0.0.0/8
                return True
            if first == 172 and 16 <= second <= 31:  # 172.16.0.0/12
                return True
            if first == 192 and second == 168:  # 192.168.0.0/16
                return True
            if first == 169 and second == 254:  # 169.254.0.0/16 (link-local)
                return True
                
        except (ValueError, IndexError):
            return True
            
        return False
    
    def detect_country_by_ip(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Detect country information from IP address"""
        if self._is_private_ip(ip_address) or ip_address == 'current':
            logger.info(f"Private/local IP or current request: {ip_address}, getting public IP location")
            return self.get_current_location()
        
        for service in self.services:
            try:
                logger.info(f"Trying {service['name']} for IP: {ip_address}")
                
                url = service['url'].format(ip=ip_address)
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Response from {service['name']}: {data}")
                    
                    if service['name'] == 'ipapi':
                        if data.get('status') == 'success':
                            country = data.get('country', 'Unknown')
                            logger.info(f"✅ Detected country from {service['name']}: {country}")
                            return {
                                'country': country,
                                'country_code': data.get('countryCode', 'XX'),
                                'city': data.get('city', 'Unknown'),
                                'region': data.get('regionName', 'Unknown'),
                                'ip': data.get('query', ip_address),
                                'source': service['name'],
                                'timezone': data.get('timezone', 'Unknown')
                            }
                    
                    elif service['name'] == 'ipinfo':
                        if 'country' in data:
                            country_code = data.get('country', 'XX')
                            # Convert country code to country name
                            country_names = {
                                'IN': 'India',
                                'US': 'United States', 
                                'GB': 'United Kingdom',
                                'CA': 'Canada',
                                'AU': 'Australia',
                                'DE': 'Germany',
                                'FR': 'France',
                                'JP': 'Japan',
                                'CN': 'China',
                                'BR': 'Brazil'
                            }
                            country = country_names.get(country_code, country_code)
                            logger.info(f"✅ Detected country from {service['name']}: {country}")
                            return {
                                'country': country,
                                'country_code': country_code,
                                'city': data.get('city', 'Unknown'),
                                'region': data.get('region', 'Unknown'),
                                'ip': data.get('ip', ip_address),
                                'source': service['name'],
                                'timezone': data.get('timezone', 'Unknown')
                            }
                    
                    elif service['name'] == 'ipgeolocation':
                        if 'country_name' in data:
                            country = data.get('country_name', 'Unknown')
                            logger.info(f"✅ Detected country from {service['name']}: {country}")
                            return {
                                'country': country,
                                'country_code': data.get('country_code2', 'XX'),
                                'city': data.get('city', 'Unknown'),
                                'region': data.get('state_prov', 'Unknown'),
                                'ip': ip_address,
                                'source': service['name'],
                                'timezone': data.get('time_zone', {}).get('name', 'Unknown')
                            }
                
                logger.warning(f"{service['name']} returned invalid data for {ip_address}")
                
            except Exception as e:
                logger.warning(f"Failed to get location from {service['name']}: {e}")
                continue
        
        # If all services fail, default to India (since you mentioned you're in India)
        logger.warning(f"All location services failed for IP {ip_address}, defaulting to India")
        return {
            'country': 'India',
            'country_code': 'IN', 
            'city': 'Unknown',
            'region': 'Unknown',
            'ip': ip_address,
            'source': 'fallback',
            'timezone': 'Asia/Kolkata'
        }
    
    def get_current_location(self) -> Optional[Dict[str, Any]]:
        """Get current user's location by detecting their public IP"""
        try:
            # Use the services directly to get current location
            logger.info("Getting current user's public IP location...")
            
            # Try ip-api first (most reliable for current location)
            try:
                response = requests.get('http://ip-api.com/json/', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Current location response: {data}")
                    if data.get('status') == 'success':
                        country = data.get('country', 'Unknown')
                        detected_ip = data.get('query', 'unknown')
                        logger.info(f"✅ Current location detected: {country} (IP: {detected_ip})")
                        return {
                            'country': country,
                            'country_code': data.get('countryCode', 'XX'),
                            'city': data.get('city', 'Unknown'),
                            'region': data.get('regionName', 'Unknown'),
                            'ip': detected_ip,
                            'source': 'ipapi-current',
                            'timezone': data.get('timezone', 'Unknown')
                        }
            except Exception as e:
                logger.warning(f"Failed to get current location from ip-api: {e}")
            
            # Fallback to ipinfo
            try:
                response = requests.get('https://ipinfo.io/json', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Current location response from ipinfo: {data}")
                    if 'country' in data:
                        country_code = data.get('country', 'XX')
                        country_names = {
                            'IN': 'India',
                            'US': 'United States', 
                            'GB': 'United Kingdom',
                            'CA': 'Canada',
                            'AU': 'Australia'
                        }
                        country = country_names.get(country_code, country_code)
                        detected_ip = data.get('ip', 'unknown')
                        logger.info(f"✅ Current location detected: {country} (IP: {detected_ip})")
                        return {
                            'country': country,
                            'country_code': country_code,
                            'city': data.get('city', 'Unknown'),
                            'region': data.get('region', 'Unknown'),
                            'ip': detected_ip,
                            'source': 'ipinfo-current',
                            'timezone': data.get('timezone', 'Unknown')
                        }
            except Exception as e:
                logger.warning(f"Failed to get current location from ipinfo: {e}")
            
            # If all fail, default to India (since you mentioned you're in India)
            logger.warning("Could not detect current location, defaulting to India")
            return {
                'country': 'India',
                'country_code': 'IN',
                'city': 'Unknown',
                'region': 'Unknown',
                'ip': 'current',
                'source': 'default',
                'timezone': 'Asia/Kolkata'
            }
            
        except Exception as e:
            logger.error(f"Error getting current location: {e}")
            return None
    
    def detect_country_from_request(self, request_obj=None) -> Dict[str, Any]:
        """Detect country from Flask request object"""
        try:
            # Get client IP
            client_ip = self.get_client_ip(request_obj)
            logger.info(f"Detecting country for client IP: {client_ip}")
            
            # Get location
            location_info = self.detect_country_by_ip(client_ip)
            
            if location_info:
                logger.info(f"Location detected: {location_info['country']} ({location_info['country_code']})")
                return location_info
            else:
                logger.warning("Could not detect location, using default")
                return {
                    'country': 'India',
                    'country_code': 'IN',
                    'city': 'Unknown',
                    'region': 'Unknown',
                    'ip': client_ip,
                    'source': 'default',
                    'timezone': 'Asia/Kolkata'
                }
                
        except Exception as e:
            logger.error(f"Error in detect_country_from_request: {e}")
            return {
                'country': 'India',
                'country_code': 'IN',
                'city': 'Unknown',
                'region': 'Unknown',
                'ip': 'unknown',
                'source': 'error',
                'timezone': 'Asia/Kolkata'
            }

# Global instance
location_service = LocationService()
