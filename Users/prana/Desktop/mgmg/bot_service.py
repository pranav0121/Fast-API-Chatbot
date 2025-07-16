#!/usr/bin/env python3
"""
Bot Integration Service
Handles Level 0 chatbot responses with fallback to human agents
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class BotService:
    """Manages bot interactions and escalation logic"""
    
    def __init__(self, app=None):
        self.app = app
        self.confidence_threshold = 0.7
        self.max_bot_attempts = 3
        
    def process_user_message(self, message: str, user_id: int = None, 
                           ticket_id: int = None, session_id: str = None) -> Dict:
        """
        Process user message through bot and determine if escalation is needed
        
        Returns:
            {
                'bot_response': str,
                'confidence': float,
                'escalate_to_human': bool,
                'intent': str,
                'resolution_suggested': bool
            }
        """
        
        try:
            # Get active bot configuration
            bot_config = self._get_active_bot_config()
            if not bot_config:
                return self._fallback_response(message, ticket_id, session_id)
            
            # Process message through bot
            bot_response = self._call_bot_api(message, bot_config)
            
            # Determine if escalation is needed
            escalate = self._should_escalate(bot_response, ticket_id)
            
            # Log interaction
            self._log_bot_interaction(
                ticket_id=ticket_id,
                user_message=message,
                bot_response=bot_response['response'],
                confidence=bot_response['confidence'],
                intent=bot_response.get('intent'),
                escalated=escalate,
                session_id=session_id
            )
            
            return {
                'bot_response': bot_response['response'],
                'confidence': bot_response['confidence'],
                'escalate_to_human': escalate,
                'intent': bot_response.get('intent'),
                'resolution_suggested': bot_response.get('resolution_suggested', False)
            }
            
        except Exception as e:
            logger.error(f"Bot processing error: {e}")
            return self._fallback_response(message, ticket_id, session_id)
    
    def _get_active_bot_config(self) -> Optional[Dict]:
        """Get active bot configuration"""
        from app import db
        from models import BotConfiguration
        
        try:
            config = BotConfiguration.query.filter_by(is_active=True).first()
            if config:
                return {
                    'id': config.id,
                    'name': config.name,
                    'bot_type': config.bot_type,
                    'api_endpoint': config.api_endpoint,
                    'api_key': config.api_key,
                    'confidence_threshold': config.confidence_threshold,
                    'config_data': json.loads(config.config_data) if config.config_data else {}
                }
            return None
        except Exception as e:
            logger.error(f"Error getting bot config: {e}")
            return None
    
    def _call_bot_api(self, message: str, bot_config: Dict) -> Dict:
        """Call external bot API (Dialogflow, Rasa, etc.)"""
        
        bot_type = bot_config['bot_type']
        
        if bot_type == 'dialogflow':
            return self._call_dialogflow(message, bot_config)
        elif bot_type == 'rasa':
            return self._call_rasa(message, bot_config)
        elif bot_type == 'custom':
            return self._call_custom_bot(message, bot_config)
        else:
            return self._get_rule_based_response(message)
    
    def _call_dialogflow(self, message: str, bot_config: Dict) -> Dict:
        """Call Google Dialogflow API"""
        try:
            # This is a simplified example - in production you'd use the Dialogflow client library
            endpoint = bot_config['api_endpoint']
            headers = {
                'Authorization': f'Bearer {bot_config["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'queryInput': {
                    'text': {
                        'text': message,
                        'languageCode': 'en-US'
                    }
                }
            }
            
            response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'response': data.get('queryResult', {}).get('fulfillmentText', 'I need to connect you with a human agent.'),
                    'confidence': data.get('queryResult', {}).get('intentDetectionConfidence', 0.5),
                    'intent': data.get('queryResult', {}).get('intent', {}).get('displayName'),
                    'resolution_suggested': data.get('queryResult', {}).get('allRequiredParamsPresent', False)
                }
            else:
                logger.error(f"Dialogflow API error: {response.status_code}")
                return self._get_fallback_bot_response(message)
                
        except requests.RequestException as e:
            logger.error(f"Dialogflow request error: {e}")
            return self._get_fallback_bot_response(message)
    
    def _call_rasa(self, message: str, bot_config: Dict) -> Dict:
        """Call Rasa bot API"""
        try:
            endpoint = f"{bot_config['api_endpoint']}/webhooks/rest/webhook"
            
            payload = {
                'sender': 'user',
                'message': message
            }
            
            response = requests.post(endpoint, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    bot_message = data[0].get('text', 'Let me connect you with a human agent.')
                    confidence = data[0].get('confidence', 0.5)
                    
                    return {
                        'response': bot_message,
                        'confidence': confidence,
                        'intent': data[0].get('intent'),
                        'resolution_suggested': confidence > 0.8
                    }
                else:
                    return self._get_fallback_bot_response(message)
            else:
                logger.error(f"Rasa API error: {response.status_code}")
                return self._get_fallback_bot_response(message)
                
        except requests.RequestException as e:
            logger.error(f"Rasa request error: {e}")
            return self._get_fallback_bot_response(message)
    
    def _call_custom_bot(self, message: str, bot_config: Dict) -> Dict:
        """Call custom bot API"""
        try:
            endpoint = bot_config['api_endpoint']
            headers = {'Authorization': f'Bearer {bot_config["api_key"]}'}
            
            payload = {
                'message': message,
                'config': bot_config['config_data']
            }
            
            response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'response': data.get('response', 'Let me connect you with a human agent.'),
                    'confidence': data.get('confidence', 0.5),
                    'intent': data.get('intent'),
                    'resolution_suggested': data.get('resolved', False)
                }
            else:
                return self._get_fallback_bot_response(message)
                
        except requests.RequestException as e:
            logger.error(f"Custom bot request error: {e}")
            return self._get_fallback_bot_response(message)
    
    def _get_rule_based_response(self, message: str) -> Dict:
        """Simple rule-based responses for common queries"""
        
        message_lower = message.lower()
        
        # Common patterns and responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return {
                'response': 'Hello! I\'m here to help you with your support request. How can I assist you today?',
                'confidence': 0.9,
                'intent': 'greeting',
                'resolution_suggested': False
            }
        
        elif any(word in message_lower for word in ['password', 'login', 'sign in', 'access']):
            return {
                'response': 'For password and login issues, I can help you reset your password. Would you like me to send you a password reset link to your registered email?',
                'confidence': 0.8,
                'intent': 'password_help',
                'resolution_suggested': True
            }
        
        elif any(word in message_lower for word in ['billing', 'payment', 'invoice', 'charge']):
            return {
                'response': 'I can help with billing questions. Are you looking for your latest invoice, need to update payment information, or have a question about charges?',
                'confidence': 0.8,
                'intent': 'billing_inquiry',
                'resolution_suggested': False
            }
        
        elif any(word in message_lower for word in ['bug', 'error', 'broken', 'not working']):
            return {
                'response': 'I understand you\'re experiencing a technical issue. Can you please describe what you were trying to do when the problem occurred?',
                'confidence': 0.7,
                'intent': 'technical_issue',
                'resolution_suggested': False
            }
        
        elif any(word in message_lower for word in ['cancel', 'refund', 'money back']):
            return {
                'response': 'I\'ll connect you with a human agent who can help with cancellation and refund requests. Please hold on.',
                'confidence': 0.6,
                'intent': 'cancellation_request',
                'resolution_suggested': False
            }
        
        else:
            return {
                'response': 'Thank you for your message. Let me connect you with one of our human support agents who can better assist you with your specific request.',
                'confidence': 0.4,
                'intent': 'general_inquiry',
                'resolution_suggested': False
            }
    
    def _get_fallback_bot_response(self, message: str) -> Dict:
        """Fallback response when bot APIs fail"""
        return {
            'response': 'I\'m currently experiencing some technical difficulties. Let me connect you with a human agent who can help you right away.',
            'confidence': 0.3,
            'intent': 'bot_error',
            'resolution_suggested': False
        }
    
    def _should_escalate(self, bot_response: Dict, ticket_id: int = None) -> bool:
        """Determine if the conversation should be escalated to human"""
        
        # Always escalate if confidence is below threshold
        if bot_response['confidence'] < self.confidence_threshold:
            return True
        
        # Check if bot has already attempted to help this ticket multiple times
        if ticket_id:
            attempt_count = self._get_bot_attempt_count(ticket_id)
            if attempt_count >= self.max_bot_attempts:
                return True
        
        # Escalate for specific intents that require human intervention
        escalation_intents = ['cancellation_request', 'refund_request', 'legal_issue', 'complaint']
        if bot_response.get('intent') in escalation_intents:
            return True
        
        return False
    
    def _get_bot_attempt_count(self, ticket_id: int) -> int:
        """Get number of bot attempts for this ticket"""
        from app import db
        from models import BotInteraction
        
        try:
            count = BotInteraction.query.filter_by(ticket_id=ticket_id).count()
            return count
        except Exception as e:
            logger.error(f"Error getting bot attempt count: {e}")
            return 0
    
    def _log_bot_interaction(self, ticket_id: int, user_message: str, bot_response: str,
                           confidence: float, intent: str = None, escalated: bool = False,
                           session_id: str = None):
        """Log bot interaction for analytics"""
        from app import db
        from models import BotInteraction
        
        try:
            interaction = BotInteraction(
                ticket_id=ticket_id,
                user_message=user_message,
                bot_response=bot_response,
                confidence_score=confidence,
                intent_detected=intent,
                escalated_to_human=escalated,
                session_id=session_id
            )
            
            db.session.add(interaction)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging bot interaction: {e}")
            db.session.rollback()
    
    def _fallback_response(self, message: str, ticket_id: int = None, 
                          session_id: str = None) -> Dict:
        """Complete fallback when no bot is configured"""
        
        response = "Thank you for contacting support. I'll connect you with one of our agents who can help you with your request."
        
        self._log_bot_interaction(
            ticket_id=ticket_id,
            user_message=message,
            bot_response=response,
            confidence=0.1,
            intent='no_bot_configured',
            escalated=True,
            session_id=session_id
        )
        
        return {
            'bot_response': response,
            'confidence': 0.1,
            'escalate_to_human': True,
            'intent': 'no_bot_configured',
            'resolution_suggested': False
        }
    
    def test_connection(self) -> Dict:
        """Test bot connection"""
        try:
            bot_config = self._get_active_bot_config()
            if not bot_config:
                return {
                    'success': False,
                    'message': 'No active bot configuration found'
                }
            
            # Try to send a test message
            test_response = self._call_bot_api("test connection", bot_config)
            
            if test_response.get('response'):
                return {
                    'success': True,
                    'message': f'Bot connection successful. Response: {test_response["response"]}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Bot connection failed - no response received'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Bot connection failed: {str(e)}'
            }
    
    def process_query(self, message: str, ticket_id: int = None, session_id: str = None, test_mode: bool = False) -> Dict:
        """Process query with test mode support"""
        if test_mode:
            # In test mode, just try to get a response without logging
            try:
                bot_config = self._get_active_bot_config()
                if not bot_config:
                    return {
                        'response': 'No bot configuration available',
                        'confidence': 0
                    }
                
                bot_response = self._call_bot_api(message, bot_config)
                return {
                    'response': bot_response.get('response', 'No response'),
                    'confidence': bot_response.get('confidence', 0)
                }
            except Exception as e:
                return {
                    'response': f'Error: {str(e)}',
                    'confidence': 0
                }
        else:
            # Normal processing
            return self.process_message(message, ticket_id, session_id)

# Global bot service instance
bot_service = BotService()
