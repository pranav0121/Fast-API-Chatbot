"""
Odoo Integration Service for Chatbot Cloud System - FIXED VERSION
Handles all Odoo API interactions using XML-RPC with redirect handling
"""

import xmlrpc.client
import ssl
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class OdooService:
    """Service class for Odoo API integration with redirect handling"""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        """
        Initialize Odoo service with proper redirect handling
        """
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        
        # Create SSL context that allows redirects and self-signed certificates
        try:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        except:
            self.ssl_context = ssl._create_unverified_context()
        
        # Try different URL formats to handle redirects
        self.working_url = self._find_working_url()
        
        # Initialize XML-RPC clients
        try:
            self.common = xmlrpc.client.ServerProxy(
                f'{self.working_url}/xmlrpc/2/common',
                context=self.ssl_context,
                allow_none=True
            )
            self.models = xmlrpc.client.ServerProxy(
                f'{self.working_url}/xmlrpc/2/object',
                context=self.ssl_context,
                allow_none=True
            )
            
            # Authenticate
            self.authenticate()
            logger.info(f"Successfully connected to Odoo at {self.working_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {e}")
            # Don't raise the error, just log it and continue
            self.common = None
            self.models = None
            self.uid = None
    
    def _find_working_url(self) -> str:
        """Find the working URL by trying different variations"""
        
        # List of possible URL formats
        urls_to_try = [
            self.url,
            self.url.replace('https://', 'http://'),
            f"https://{self.url.replace('https://', '').replace('http://', '')}",
            f"http://{self.url.replace('https://', '').replace('http://', '')}"
        ]
        
        for test_url in urls_to_try:
            try:
                # Test basic connectivity
                import urllib.request
                req = urllib.request.Request(test_url)
                with urllib.request.urlopen(req, context=self.ssl_context, timeout=10) as response:
                    final_url = response.geturl().rstrip('/')
                    logger.info(f"Found working URL: {final_url}")
                    return final_url
            except Exception as e:
                logger.debug(f"URL {test_url} failed: {e}")
                continue
        
        # If no URL works, return original
        logger.warning(f"No working URL found, using original: {self.url}")
        return self.url
    
    def authenticate(self) -> Optional[int]:
        """Authenticate with Odoo and get user ID"""
        if not self.common:
            return None
            
        try:
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                raise Exception("Authentication failed - check credentials")
            logger.info(f"Authenticated as user ID: {self.uid}")
            return self.uid
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.uid = None
            return None
    
    def is_connected(self) -> bool:
        """Check if Odoo connection is working"""
        return self.common is not None and self.models is not None and self.uid is not None
    
    def create_customer(self, name: str, email: str, phone: str = None, organization: str = None, comment: str = None) -> Optional[int]:
        """Create a customer in Odoo"""
        if not self.is_connected():
            logger.warning("Odoo not connected, skipping customer creation")
            return None
            
        try:
            partner_data = {
                'name': name,
                'email': email,
                'is_company': False,
                'customer_rank': 1,
            }
            
            if phone:
                partner_data['phone'] = phone
            if organization:
                partner_data['parent_name'] = organization
            if comment:
                partner_data['comment'] = comment
            
            partner_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'create', [partner_data]
            )
            
            logger.info(f"Created customer {name} with ID {partner_id}")
            return partner_id
            
        except Exception as e:
            logger.error(f"Failed to create customer: {e}")
            return None
    
    def create_ticket(self, name: str, description: str, partner_id: int = None, 
                     priority: str = '1', tag_ids: List[str] = None) -> Optional[int]:
        """Create a helpdesk ticket in Odoo"""
        if not self.is_connected():
            logger.warning("Odoo not connected, skipping ticket creation")
            return None
            
        try:
            # Find or create tag
            processed_tag_ids = []
            if tag_ids:
                for tag_name in tag_ids:
                    tag_id = self._find_or_create_tag(tag_name)
                    if tag_id:
                        processed_tag_ids.append((4, tag_id))
            
            ticket_data = {
                'name': name,
                'description': description,
                'priority': priority,
            }
            
            if partner_id:
                ticket_data['partner_id'] = partner_id
            if processed_tag_ids:
                ticket_data['tag_ids'] = processed_tag_ids
            
            ticket_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'helpdesk.ticket', 'create', [ticket_data]
            )
            
            logger.info(f"Created ticket '{name}' with ID {ticket_id}")
            return ticket_id
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return None
    
    def _find_or_create_tag(self, tag_name: str) -> Optional[int]:
        """Find or create a helpdesk tag"""
        if not self.is_connected():
            return None
            
        try:
            # Search for existing tag
            existing_tags = self.models.execute_kw(
                self.db, self.uid, self.password,
                'helpdesk.tag', 'search_read',
                [[['name', '=', tag_name]]], {'fields': ['id', 'name']}
            )
            
            if existing_tags:
                logger.info(f"Found existing tag '{tag_name}' with ID {existing_tags[0]['id']}")
                return existing_tags[0]['id']
            
            # Create new tag
            tag_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'helpdesk.tag', 'create', [{'name': tag_name}]
            )
            
            logger.info(f"Created new tag '{tag_name}' with ID {tag_id}")
            return tag_id
            
        except Exception as e:
            logger.error(f"Failed to find/create tag '{tag_name}': {e}")
            return None

# Create a function to initialize Odoo service safely
def create_odoo_service(url: str, db: str, username: str, password: str) -> Optional[OdooService]:
    """Create Odoo service with error handling"""
    try:
        service = OdooService(url, db, username, password)
        if service.is_connected():
            return service
        else:
            logger.warning("Odoo service created but not connected")
            return None
    except Exception as e:
        logger.error(f"Failed to create Odoo service: {e}")
        return None
