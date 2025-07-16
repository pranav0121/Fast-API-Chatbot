#!/usr/bin/env python3
"""
Device Tracking Module for Chatbot Cloud - Standalone Components
Core device tracking functionality without Flask dependencies
"""

import re
import json
from datetime import datetime

# Simple user agent parsing without external dependencies
class SimpleUserAgentParser:
    """Simple user agent parser that doesn't require external libraries"""
    
    def __init__(self, user_agent_string):
        self.user_agent_string = user_agent_string or ""
        self.ua_lower = self.user_agent_string.lower()
    
    def get_browser_info(self):
        """Extract browser information from user agent"""
        browser_patterns = {
            'chrome': r'chrome/([\d.]+)',
            'firefox': r'firefox/([\d.]+)',
            'safari': r'version/([\d.]+).*safari',
            'edge': r'edge/([\d.]+)',
            'opera': r'opera/([\d.]+)',
            'internet explorer': r'msie ([\d.]+)'
        }
        
        for browser, pattern in browser_patterns.items():
            match = re.search(pattern, self.ua_lower)
            if match:
                return {
                    'family': browser.title(),
                    'version_string': match.group(1),
                    'version': [int(x) for x in match.group(1).split('.') if x.isdigit()]
                }
        
        return {
            'family': 'Unknown',
            'version_string': '0.0',
            'version': [0, 0]
        }
    
    def get_os_info(self):
        """Extract OS information from user agent"""
        os_patterns = {
            'windows': r'windows nt ([\d.]+)',
            'macos': r'mac os x ([\d_]+)',
            'ios': r'os ([\d_]+)',
            'android': r'android ([\d.]+)',
            'linux': r'linux'
        }
        
        for os_name, pattern in os_patterns.items():
            match = re.search(pattern, self.ua_lower)
            if match:
                if len(match.groups()) > 0:
                    version = match.group(1).replace('_', '.')
                    return {
                        'family': os_name.title(),
                        'version_string': version,
                        'version': [int(x) for x in version.split('.') if x.isdigit()]
                    }
                else:
                    return {
                        'family': os_name.title(),
                        'version_string': 'Unknown',
                        'version': [0]
                    }
        
        return {
            'family': 'Unknown',
            'version_string': 'Unknown',
            'version': [0]
        }
    
    @property
    def is_mobile(self):
        """Check if device is mobile"""
        mobile_patterns = [
            'mobile', 'android', 'iphone', 'ipod', 'blackberry',
            'windows phone', 'palm', 'symbian'
        ]
        return any(pattern in self.ua_lower for pattern in mobile_patterns)
    
    @property
    def is_tablet(self):
        """Check if device is tablet"""
        tablet_patterns = ['ipad', 'tablet', 'kindle']
        return any(pattern in self.ua_lower for pattern in tablet_patterns)
    
    @property
    def is_pc(self):
        """Check if device is PC/desktop"""
        return not (self.is_mobile or self.is_tablet)
    
    @property
    def is_bot(self):
        """Check if user agent indicates a bot"""
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'googlebot', 'bingbot', 'facebookexternalhit'
        ]
        return any(pattern in self.ua_lower for pattern in bot_patterns)

class DeviceInfo:
    """Device information parser and tracker - Standalone version"""
    
    def __init__(self, user_agent_string=None, ip_address=None):
        self.user_agent_string = user_agent_string or "Unknown"
        self.ip_address = ip_address or "Unknown"
        self.parsed_ua = SimpleUserAgentParser(self.user_agent_string)
    
    def get_device_type(self):
        """Determine device type"""
        if self.parsed_ua.is_mobile:
            return 'mobile'
        elif self.parsed_ua.is_tablet:
            return 'tablet'
        elif self.parsed_ua.is_pc:
            return 'desktop'
        else:
            return 'unknown'
    
    def get_browser_info(self):
        """Get detailed browser information"""
        return self.parsed_ua.get_browser_info()
    
    def get_os_info(self):
        """Get operating system information"""
        return self.parsed_ua.get_os_info()
    
    def is_bot(self):
        """Check if user agent indicates a bot/crawler"""
        return self.parsed_ua.is_bot
    
    def get_complete_info(self):
        """Get complete device information as dictionary"""
        return {
            'user_agent': self.user_agent_string,
            'ip_address': self.ip_address,
            'device_type': self.get_device_type(),
            'is_mobile': self.parsed_ua.is_mobile,
            'is_tablet': self.parsed_ua.is_tablet,
            'is_pc': self.parsed_ua.is_pc,
            'is_bot': self.is_bot(),
            'browser': self.get_browser_info(),
            'os': self.get_os_info(),
            'timestamp': datetime.utcnow().isoformat()
        }

class DeviceAnalytics:
    """Device analytics and reporting - Standalone version"""
    
    @staticmethod
    def get_device_stats():
        """Get device usage statistics"""
        return {
            'device_types': {
                'desktop': 60,
                'mobile': 35,
                'tablet': 5
            },
            'browsers': {
                'Chrome': 50,
                'Firefox': 20,
                'Safari': 15,
                'Edge': 10,
                'Other': 5
            },
            'operating_systems': {
                'Windows': 45,
                'Android': 25,
                'iOS': 15,
                'macOS': 10,
                'Linux': 3,
                'Other': 2
            }
        }
    
    @staticmethod
    def get_compatibility_info(device_info):
        """Get device compatibility information for support"""
        browser = device_info.get_browser_info()
        os = device_info.get_os_info()
        
        # Define compatibility rules
        compatibility = {
            'websocket_support': True,
            'file_upload_support': True,
            'notifications_support': True,
            'issues': []
        }
        
        # Check for known compatibility issues
        if browser['family'] == 'Internet Explorer':
            compatibility['issues'].append('Internet Explorer is not fully supported. Please use Chrome, Firefox, or Edge.')
            compatibility['websocket_support'] = False
            
        if device_info.get_device_type() == 'mobile' and browser['family'] == 'Safari':
            compatibility['issues'].append('Some features may be limited on mobile Safari.')
            
        return compatibility

# Export main classes
__all__ = [
    'SimpleUserAgentParser',
    'DeviceInfo',
    'DeviceAnalytics'
]
