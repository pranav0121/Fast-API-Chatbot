#!/usr/bin/env python3
"""
Extended Database Models for Enterprise Super Admin Portal
"""

from datetime import datetime
from app import db

class Partner(db.Model):
    """Partner Management for ICP/YCP"""
    __tablename__ = 'partners'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    partner_type = db.Column(db.String(50), nullable=False)  # ICP, YCP
    email = db.Column(db.String(255), nullable=False, unique=True)
    contact_person = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, suspended
    api_key = db.Column(db.String(255), nullable=True)
    webhook_url = db.Column(db.String(500), nullable=True)
    escalation_settings = db.Column(db.Text, nullable=True)  # JSON
    sla_settings = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Statistics
    total_tickets_handled = db.Column(db.Integer, default=0)
    avg_resolution_time = db.Column(db.Float, default=0.0)  # in hours
    satisfaction_rating = db.Column(db.Float, default=0.0)

class SLALog(db.Model):
    """SLA Tracking and Monitoring"""
    __tablename__ = 'sla_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('Tickets.TicketID'), nullable=False)
    escalation_level = db.Column(db.Integer, nullable=False)  # 0=Bot, 1=ICP, 2=YouCloud
    level_name = db.Column(db.String(50), nullable=False)  # Bot, ICP, YouCloud
    sla_target_hours = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='on_time')  # on_time, at_risk, breached
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    escalated_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    is_breached = db.Column(db.Boolean, default=False)
    breach_time = db.Column(db.DateTime, nullable=True)
    resolution_method = db.Column(db.String(50), nullable=True)  # Bot, ICP, YouCloud
    assigned_partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=True)
    
    # Relationships
    ticket = db.relationship('Ticket', backref=db.backref('sla_logs', lazy=True))
    assigned_partner = db.relationship('Partner', backref=db.backref('sla_logs', lazy=True))

class TicketStatusLog(db.Model):
    """Workflow Logs / Timeline View"""
    __tablename__ = 'ticket_status_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('Tickets.TicketID'), nullable=False)
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    changed_by = db.Column(db.String(255), nullable=True)  # Name of who changed it
    changed_by_id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=True)
    changed_by_type = db.Column(db.String(20), nullable=False)  # user, admin, system, bot
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    escalation_level = db.Column(db.Integer, nullable=True)
    sla_status = db.Column(db.String(20), default='on_time')  # on_time, at_risk, breached
    notes = db.Column(db.Text, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)  # JSON for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = db.relationship('Ticket', backref=db.backref('status_logs', lazy=True))
    changed_by_user = db.relationship('User', backref=db.backref('status_changes', lazy=True))

class AuditLog(db.Model):
    """Comprehensive Audit Logging"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # ticket, user, partner, etc.
    resource_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=True)
    user_type = db.Column(db.String(20), nullable=False)  # admin, user, system, api
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON with action details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

class EscalationRule(db.Model):
    """Automated Escalation Rules"""
    __tablename__ = 'escalation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    priority = db.Column(db.String(20), nullable=False)  # critical, high, medium, low
    category_id = db.Column(db.Integer, db.ForeignKey('Categories.CategoryID'), nullable=True)
    level_0_sla_hours = db.Column(db.Float, default=0.0)  # Bot response time
    level_1_sla_hours = db.Column(db.Float, default=4.0)  # ICP response time
    level_2_sla_hours = db.Column(db.Float, default=24.0)  # YouCloud response time
    auto_escalate = db.Column(db.Boolean, default=True)
    notification_enabled = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref=db.backref('escalation_rules', lazy=True))

class BotConfiguration(db.Model):
    """Bot Integration Configuration"""
    __tablename__ = 'bot_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    bot_type = db.Column(db.String(50), nullable=False)  # dialogflow, rasa, custom
    api_endpoint = db.Column(db.String(500), nullable=True)
    api_key = db.Column(db.String(255), nullable=True)
    config_data = db.Column(db.Text, nullable=True)  # JSON configuration
    is_active = db.Column(db.Boolean, default=True)
    fallback_to_human = db.Column(db.Boolean, default=True)
    confidence_threshold = db.Column(db.Float, default=0.7)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BotInteraction(db.Model):
    """Bot Interaction Logs"""
    __tablename__ = 'bot_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('Tickets.TicketID'), nullable=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)
    intent_detected = db.Column(db.String(255), nullable=True)
    was_resolved = db.Column(db.Boolean, default=False)
    escalated_to_human = db.Column(db.Boolean, default=False)
    success = db.Column(db.Boolean, default=True)  # Whether the interaction was successful
    response_time = db.Column(db.Float, nullable=True)  # Response time in milliseconds
    session_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = db.relationship('Ticket', backref=db.backref('bot_interactions', lazy=True))

# Extended Ticket model fields (we'll add these via migrations)
"""
Additional fields to add to existing Ticket model:
- escalation_level (Integer, default=0)
- current_sla_target (DateTime)
- resolution_method (String(50))
- bot_attempted (Boolean, default=False)
- partner_id (Integer, ForeignKey to partners.id)
"""

