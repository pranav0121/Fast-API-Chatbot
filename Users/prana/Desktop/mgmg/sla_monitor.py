#!/usr/bin/env python3
"""
SLA Monitoring Service
Automated SLA tracking, breach detection, and escalation
"""

import json
import logging
from datetime import datetime, timedelta, timedelta
from typing import List, Dict, Optional
import threading
import time

logger = logging.getLogger(__name__)

class SLAMonitor:
    """Monitors SLA compliance and handles automatic escalations"""
    
    def __init__(self, app=None):
        self.app = app
        self.monitoring = False
        self.check_interval = 300  # Check every 5 minutes
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start the SLA monitoring service"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("SLA monitoring service started")
    
    def stop_monitoring(self):
        """Stop the SLA monitoring service"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("SLA monitoring service stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                with self.app.app_context():
                    # Check if tables exist before trying to monitor
                    if self._tables_exist():
                        self._check_sla_compliance()
                        self._process_escalations()
                        self.check_and_auto_escalate_tickets()  # Enhanced auto-escalation
                    else:
                        logger.info("SLA monitoring waiting for database tables to be created...")
                    
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in SLA monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _tables_exist(self):
        """Check if required tables exist"""
        try:
            from app import db
            from sqlalchemy import text
            
            # Check if the new columns exist in Tickets table
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'Tickets' AND COLUMN_NAME IN ('escalation_level', 'current_sla_target')
            """))
            
            columns = [row[0] for row in result]
            
            # Also check if sla_logs table exists
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'sla_logs'
            """))
            
            sla_table_exists = len(list(result)) > 0
            return len(columns) >= 2 and sla_table_exists
            
        except ImportError as ie:
            # Handle circular import specifically
            logger.debug(f"Import error checking table existence (expected during startup): {ie}")
            return False
        except Exception as e:
            logger.debug(f"Error checking table existence: {e}")
            return False
    
    def _check_sla_compliance(self):
        """Check all active tickets for SLA compliance"""
        try:
            from app import db, Ticket
            # Import models here to avoid circular import
            try:
                from models import SLALog, EscalationRule
            except ImportError:
                logger.debug("Models not yet available, skipping SLA compliance check")
                return
            
            # Get all active tickets
            active_tickets = Ticket.query.filter(
                Ticket.Status.in_(['open', 'in_progress', 'escalated'])
            ).all()
            
            for ticket in active_tickets:
                # Get or create SLA log for this ticket
                sla_log = SLALog.query.filter_by(ticket_id=ticket.TicketID).first()
                
                if not sla_log:
                    # Create initial SLA log
                    sla_log = self._create_initial_sla_log(ticket)
                
                # Check if SLA is breached
                if sla_log and not sla_log.is_breached:
                    is_breached = self._check_sla_breach(sla_log)
                    
                    if is_breached:
                        sla_log.is_breached = True
                        sla_log.breach_time = datetime.utcnow()
                        
                        # Trigger escalation
                        self._trigger_escalation(ticket, sla_log)
                        
                        logger.warning(f"SLA breached for ticket {ticket.TicketID}")
                
                db.session.commit()
                
        except ImportError as ie:
            logger.debug(f"Import error in SLA compliance check (expected during startup): {ie}")
        except Exception as e:
            logger.error(f"Error checking SLA compliance: {e}")
            try:
                from app import db
                db.session.rollback()
            except:
                pass
    
    def _create_initial_sla_log(self, ticket):
        """Create initial SLA log for a ticket"""
        try:
            from app import db
            # Import models here to avoid circular import
            try:
                from models import SLALog, EscalationRule
            except ImportError:
                logger.debug("Models not yet available, cannot create SLA log")
                return None
            
            # Get escalation rule for this ticket
            escalation_rule = EscalationRule.query.filter_by(
                priority=ticket.Priority,
                is_active=True
            ).first()
            
            if not escalation_rule:
                # Use default SLA times
                sla_hours = {
                    'critical': 1.0,
                    'high': 4.0,
                    'medium': 8.0,
                    'low': 24.0
                }.get(ticket.Priority, 8.0)
            else:
                sla_hours = escalation_rule.level_1_sla_hours
            
            sla_log = SLALog(
                ticket_id=ticket.TicketID,
                escalation_level=0,  # Start at bot level
                level_name='Bot',
                sla_target_hours=sla_hours
            )
            
            db.session.add(sla_log)
            return sla_log
            
        except ImportError as ie:
            logger.debug(f"Import error creating SLA log (expected during startup): {ie}")
            return None
        except Exception as e:
            logger.error(f"Error creating initial SLA log: {e}")
            return None
    
    def _check_sla_breach(self, sla_log) -> bool:
        """Check if SLA is breached for a given log entry"""
        if not sla_log.created_at:
            logger.warning(f"SLA log {sla_log.id} has no created_at timestamp")
            return False
            
        target_time = sla_log.created_at + timedelta(hours=sla_log.sla_target_hours)
        return datetime.utcnow() > target_time
    
    def _trigger_escalation(self, ticket, sla_log):
        """Trigger escalation to next level"""
        try:
            from app import db
            # Import models here to avoid circular import
            try:
                from models import TicketStatusLog, EscalationRule, SLALog
            except ImportError:
                logger.debug("Models not yet available, cannot trigger escalation")
                return
            
            # Determine next escalation level
            current_level = sla_log.escalation_level
            next_level = min(current_level + 1, 2)  # Max level is 2 (YouCloud)
            
            # Get escalation rule
            escalation_rule = EscalationRule.query.filter_by(
                priority=ticket.Priority,
                is_active=True
            ).first()
            
            # Update ticket escalation level
            ticket.escalation_level = next_level
            
            # Create new SLA log for next level
            level_names = ['Bot', 'ICP', 'YouCloud']
            
            if escalation_rule:
                sla_hours = [
                    escalation_rule.level_0_sla_hours,
                    escalation_rule.level_1_sla_hours,
                    escalation_rule.level_2_sla_hours
                ][next_level]
            else:
                # Default SLA hours
                sla_hours = [0, 4, 24][next_level]
            
            new_sla_log = SLALog(
                ticket_id=ticket.TicketID,
                escalation_level=next_level,
                level_name=level_names[next_level],
                sla_target_hours=sla_hours,
                escalated_at=datetime.utcnow()
            )
            
            db.session.add(new_sla_log)
            
            # Create status log
            status_log = TicketStatusLog(
                ticket_id=ticket.TicketID,
                old_status=ticket.Status,
                new_status='escalated',
                changed_by_type='system',
                escalation_level=next_level,
                comment=f'Automatic escalation due to SLA breach. Escalated to {level_names[next_level]}.'
            )
            
            db.session.add(status_log)
            
            # Send notifications
            self._send_escalation_notification(ticket, next_level)
            
            logger.info(f"Ticket {ticket.TicketID} escalated to level {next_level}")
            
        except ImportError as ie:
            logger.debug(f"Import error triggering escalation (expected during startup): {ie}")
        except Exception as e:
            logger.error(f"Error triggering escalation: {e}")
            raise
    
    def _process_escalations(self):
        """Process any pending escalations"""
        try:
            from app import db, Ticket
            # Import models here to avoid circular import
            try:
                from models import SLALog
            except ImportError:
                logger.debug("Models not yet available, skipping escalation processing")
                return
            
            # Find tickets that need escalation but haven't been escalated yet
            pending_escalations = db.session.query(Ticket, SLALog).join(
                SLALog, Ticket.TicketID == SLALog.ticket_id
            ).filter(
                Ticket.Status.in_(['open', 'in_progress']),
                SLALog.is_breached == True,
                SLALog.escalated_at == None,
                SLALog.escalation_level < 2
            ).all()
            
            for ticket, sla_log in pending_escalations:
                # Mark as escalated
                sla_log.escalated_at = datetime.utcnow()
                
                # Create notification or API call to partner
                self._notify_partner_escalation(ticket, sla_log)
            
            db.session.commit()
            
        except ImportError as ie:
            logger.debug(f"Import error processing escalations (expected during startup): {ie}")
        except Exception as e:
            logger.error(f"Error processing escalations: {e}")
            try:
                from app import db
                db.session.rollback()
            except:
                pass
    
    def _send_escalation_notification(self, ticket, escalation_level):
        """Send notification about escalation"""
        level_names = ['Bot', 'ICP', 'YouCloud']
        level_name = level_names[escalation_level]
        
        # Here you would implement email, SMS, or webhook notifications
        # For now, we'll just log
        logger.info(f"ESCALATION NOTIFICATION: Ticket {ticket.TicketID} escalated to {level_name}")
        
        # You could add:
        # - Email notifications to admin team        # - Slack/Teams notifications
        # - Webhook calls to external systems
        # - SMS alerts for critical issues
    
    def _notify_partner_escalation(self, ticket, sla_log):
        """Notify partners about escalated tickets"""
        try:
            # Import models here to avoid circular import
            try:
                from models import Partner
                
                # Find appropriate partner for this escalation level
                partner_type = 'ICP' if sla_log.escalation_level == 1 else 'YCP'
                
                partners = Partner.query.filter_by(
                    partner_type=partner_type,
                    status='active'
                ).all()
                
                if partners:
                    # For now, assign to first available partner
                    # In production, you'd implement load balancing
                    partner = partners[0]
                
            except (ImportError, AttributeError) as e:
                logger.debug(f"Partner model not yet available for notifications: {e}")
                return
                
                # Update ticket with partner assignment
                from app import db, Ticket
                ticket_obj = Ticket.query.get(ticket.TicketID)
                ticket_obj.partner_id = partner.id
                
                # Send webhook notification if configured
                if partner.webhook_url:
                    self._send_webhook_notification(partner, ticket, sla_log)
                
                db.session.commit()
                
        except ImportError as ie:
            logger.debug(f"Import error notifying partners (expected during startup): {ie}")
        except Exception as e:
            logger.error(f"Error notifying partner: {e}")
    
    def _send_webhook_notification(self, partner, ticket, sla_log):
        """Send webhook notification to partner"""
        import requests
        
        try:
            payload = {
                'event': 'ticket_escalated',
                'ticket': {
                    'id': ticket.TicketID,
                    'subject': ticket.Subject,
                    'priority': ticket.Priority,
                    'status': ticket.Status,
                    'organization': ticket.OrganizationName,
                    'created_by': ticket.CreatedBy,
                    'created_at': ticket.CreatedAt.isoformat(),
                },
                'escalation': {
                    'level': sla_log.escalation_level,
                    'level_name': sla_log.level_name,
                    'sla_target_hours': sla_log.sla_target_hours,
                    'escalated_at': sla_log.escalated_at.isoformat() if sla_log.escalated_at else None
                },
                'partner': {
                    'id': partner.id,
                    'name': partner.name,
                    'type': partner.partner_type
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'YouCloud-Support-System/1.0'
            }
            
            # Add authentication if API key is configured
            if partner.api_key:
                headers['Authorization'] = f'Bearer {partner.api_key}'
            
            response = requests.post(
                partner.webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook notification sent to {partner.name}")
            else:
                logger.warning(f"Webhook notification failed for {partner.name}: {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"Webhook request failed: {e}")
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    def get_sla_statistics(self) -> Dict:
        """Get SLA compliance statistics"""
        try:
            from app import db
            # Import models here to avoid circular import
            try:
                from models import SLALog
            except ImportError:
                logger.debug("Models not yet available, returning empty statistics")
                return {
                    'overall_compliance': 0,
                    'total_tickets': 0,
                    'breached_tickets': 0,
                    'level_statistics': []
                }
            
            # Get statistics for last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            total_logs = SLALog.query.filter(
                SLALog.created_at >= thirty_days_ago
            ).count()
            
            breached_logs = SLALog.query.filter(
                SLALog.created_at >= thirty_days_ago,
                SLALog.is_breached == True
            ).count()
            
            compliance_rate = ((total_logs - breached_logs) / total_logs * 100) if total_logs > 0 else 100
            
            # Get statistics by level
            level_stats = []
            for level in range(3):
                level_total = SLALog.query.filter(
                    SLALog.created_at >= thirty_days_ago,
                    SLALog.escalation_level == level
                ).count()
                
                level_breached = SLALog.query.filter(
                    SLALog.created_at >= thirty_days_ago,
                    SLALog.escalation_level == level,
                    SLALog.is_breached == True
                ).count()
                
                level_compliance = ((level_total - level_breached) / level_total * 100) if level_total > 0 else 100
                
                level_stats.append({
                    'level': level,
                    'level_name': ['Bot', 'ICP', 'YouCloud'][level],
                    'total_tickets': level_total,
                    'breached_tickets': level_breached,
                    'compliance_rate': round(level_compliance, 2)
                })
            
            return {
                'overall_compliance': round(compliance_rate, 2),
                'total_tickets': total_logs,
                'breached_tickets': breached_logs,
                'level_statistics': level_stats
            }
            
        except ImportError as ie:
            logger.debug(f"Import error getting SLA statistics (expected during startup): {ie}")
            return {
                'overall_compliance': 0,
                'total_tickets': 0,
                'breached_tickets': 0,
                'level_statistics': []
            }
        except Exception as e:
            logger.error(f"Error getting SLA statistics: {e}")
            return {
                'overall_compliance': 0,
                'total_tickets': 0,
                'breached_tickets': 0,
                'level_statistics': []
            }
    
    def check_and_auto_escalate_tickets(self):
        """Enhanced auto-escalation with comprehensive tracking"""
        try:
            from app import db, Ticket
            import json
            
            # Get tickets approaching SLA breach (within 30 minutes) or already breached
            now = datetime.utcnow()
            warning_time = now + timedelta(minutes=30)
            
            # Find tickets that need escalation
            tickets_needing_escalation = Ticket.query.filter(
                Ticket.Status.in_(['open', 'in_progress']),
                Ticket.SLATarget.isnot(None),
                db.or_(
                    Ticket.SLATarget <= warning_time,  # Approaching breach
                    Ticket.SLATarget <= now  # Already breached
                )
            ).filter(
                # Only escalate tickets that haven't been recently escalated
                db.or_(
                    Ticket.EscalationTimestamp.is_(None),
                    Ticket.EscalationTimestamp <= now - timedelta(hours=1)  # Allow re-escalation after 1 hour
                )
            ).all()
            
            for ticket in tickets_needing_escalation:
                self._auto_escalate_ticket(ticket, now)
            
            if tickets_needing_escalation:
                db.session.commit()
                logger.info(f"Auto-escalated {len(tickets_needing_escalation)} tickets")
            
        except Exception as e:
            logger.error(f"Error in auto-escalation: {e}")
            try:
                from app import db
                db.session.rollback()
            except:
                pass
    
    def _auto_escalate_ticket(self, ticket, now):
        """Auto-escalate a single ticket based on SLA and priority"""
        try:
            import json
            
            # Determine escalation level based on current state and priority
            current_level = ticket.EscalationLevel or 'normal'
            escalation_reason = "SLA breach - automatic escalation"
            
            # Check if SLA is actually breached
            if ticket.SLATarget and ticket.SLATarget <= now:
                ticket.SLABreachStatus = "Breached"
                escalation_reason = "SLA breached - automatic escalation"
            elif ticket.SLATarget and ticket.SLATarget <= now + timedelta(minutes=30):
                ticket.SLABreachStatus = "Approaching Breach"
                escalation_reason = "SLA approaching breach - automatic escalation"
            
            # Determine next escalation level
            if current_level == 'normal':
                if ticket.Priority in ['critical', 'high']:
                    new_level = 'supervisor'
                    escalated_to = 'supervisor_auto'
                    role = 'supervisor'
                else:
                    new_level = 'supervisor'
                    escalated_to = 'supervisor_auto'
                    role = 'supervisor'
            elif current_level == 'supervisor':
                new_level = 'admin'
                escalated_to = 'admin_auto'
                role = 'admin'
            else:
                # Already at admin level, extend SLA instead
                if ticket.SLATarget:
                    ticket.SLATarget = ticket.SLATarget + timedelta(hours=2)
                    escalation_reason = "SLA extended due to admin escalation"
                return
            
            # Create escalation history entry
            escalation_entry = {
                "ticketId": f"TCK-{ticket.TicketID}",
                "escalationLevel": 1 if new_level == 'supervisor' else 2,
                "escalatedTo": escalated_to,
                "escalationReason": escalation_reason,
                "escalationTimestamp": now.isoformat() + "Z",
                "autoEscalated": True,
                "previousLevel": current_level,
                "previousRole": ticket.CurrentAssignedRole or 'bot',
                "slaBreach": ticket.SLABreachStatus
            }
            
            # Update escalation history
            if ticket.EscalationHistory:
                try:
                    history = json.loads(ticket.EscalationHistory)
                except:
                    history = []
            else:
                history = []
            
            history.append(escalation_entry)
            
            # Update ticket
            ticket.EscalationLevel = new_level
            ticket.EscalationReason = escalation_reason
            ticket.EscalationTimestamp = now
            ticket.EscalatedTo = escalated_to
            ticket.AutoEscalated = True
            ticket.EscalationHistory = json.dumps(history)
            ticket.CurrentAssignedRole = role
            ticket.UpdatedAt = now
            
            # Update status
            if ticket.Status == 'open':
                ticket.Status = 'escalated'
            
            logger.info(f"Auto-escalated ticket {ticket.TicketID} from {current_level} to {new_level} due to SLA concern")
            
        except Exception as e:
            logger.error(f"Error auto-escalating ticket {ticket.TicketID}: {e}")

# Global SLA monitor instance
sla_monitor = SLAMonitor()
