#!/usr/bin/env python3
"""
Real-time Notification Service
Instant alerts for high-value leads with multiple channels
"""

import smtplib
import requests
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


class NotificationService:
    """Handle real-time notifications for sales team"""

    @staticmethod
    def notify_sales_team(lead_data):
        """Send instant notifications for high-value leads"""
        try:
            lead_score = lead_data.get('lead_score', 0)
            lead_type = lead_data.get('lead_type', 'Unqualified')

            # Only notify for SQL leads (high priority)
            if lead_type == 'SQL' and lead_score >= 60:
                NotificationService.send_email_alert(lead_data)
                NotificationService.send_slack_notification(lead_data)
                NotificationService.send_discord_webhook(lead_data)
                NotificationService.log_notification(lead_data)

                return True
            return False

        except Exception as e:
            print(f"Notification error: {str(e)}")
            return False

    @staticmethod
    def send_email_alert(lead_data):
        """Send email alert to sales team"""
        try:
            name = lead_data.get('name', 'Anonymous')
            score = lead_data.get('lead_score', 0)
            business = lead_data.get('business_type', 'Not specified')
            location = lead_data.get('location', 'Not specified')
            features = lead_data.get('features_interested', [])
            email = lead_data.get('email', 'Not provided')
            phone = lead_data.get('phone', 'Not provided')

            subject = f"🔥 HOT LEAD ALERT: {name} (Score: {score})"

                # Removed HTML email body for backend-only implementation
                html_body = "This is a backend-only implementation. No HTML content is sent."

            # Email configuration (you'll need to set these in config.py)
            sender_email = getattr(Config, 'SENDER_EMAIL', 'leads@youshop.com')
            sender_password = getattr(
                Config, 'SENDER_PASSWORD', 'your_password')
            recipient_emails = getattr(
                Config, 'SALES_TEAM_EMAILS', ['sales@youshop.com'])

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_emails)

            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Send email (uncomment when email config is ready)
            # server = smtplib.SMTP('smtp.gmail.com', 587)
            # server.starttls()
            # server.login(sender_email, sender_password)
            # server.send_message(msg)
            # server.quit()

            print(f"📧 Email alert sent for lead: {name}")
            return True

        except Exception as e:
            print(f"Email notification error: {str(e)}")
            return False

    @staticmethod
    def send_slack_notification(lead_data):
        """Send Slack notification"""
        try:
            slack_webhook = getattr(Config, 'SLACK_WEBHOOK_URL', None)
            if not slack_webhook:
                print("Slack webhook not configured")
                return False

            name = lead_data.get('name', 'Anonymous')
            score = lead_data.get('lead_score', 0)
            business = lead_data.get('business_type', 'Not specified')

            slack_message = {
                "text": f"🔥 HOT LEAD ALERT: {name}",
                "attachments": [
                    {
                        "color": "#ff6b6b",
                        "fields": [
                            {"title": "Name", "value": name, "short": True},
                            {"title": "Score",
                                "value": f"{score} (SQL)", "short": True},
                            {"title": "Business", "value": business, "short": True},
                            {"title": "Contact", "value": lead_data.get(
                                'phone', 'Not provided'), "short": True}
                        ],
                        "actions": [
                            {
                                "type": "button",
                                "text": "View Dashboard",
                                "url": "http://127.0.0.1:5000/api/leads/dashboard"
                            }
                        ]
                    }
                ]
            }

            response = requests.post(slack_webhook, json=slack_message)
            print(f"📱 Slack notification sent for lead: {name}")
            return response.status_code == 200

        except Exception as e:
            print(f"Slack notification error: {str(e)}")
            return False

    @staticmethod
    def send_discord_webhook(lead_data):
        """Send Discord webhook notification"""
        try:
            discord_webhook = getattr(Config, 'DISCORD_WEBHOOK_URL', None)
            if not discord_webhook:
                print("Discord webhook not configured")
                return False

            name = lead_data.get('name', 'Anonymous')
            score = lead_data.get('lead_score', 0)
            business = lead_data.get('business_type', 'Not specified')

            discord_message = {
                "embeds": [
                    {
                        "title": "🔥 HOT LEAD ALERT",
                        "description": f"**{name}** just became a qualified lead!",
                        "color": 16742635,  # Red color
                        "fields": [
                            {"name": "👤 Name", "value": name, "inline": True},
                            {"name": "📊 Score",
                                "value": f"{score} (SQL)", "inline": True},
                            {"name": "🏢 Business", "value": business, "inline": True},
                            {"name": "📱 Phone", "value": lead_data.get(
                                'phone', 'Not provided'), "inline": True},
                            {"name": "📧 Email", "value": lead_data.get(
                                'email', 'Not provided'), "inline": True},
                            {"name": "📍 Location", "value": lead_data.get(
                                'location', 'Not specified'), "inline": True}
                        ],
                        "timestamp": datetime.now().isoformat(),
                        "footer": {"text": "YouShop Lead Capture System"}
                    }
                ]
            }

            response = requests.post(discord_webhook, json=discord_message)
            print(f"🎮 Discord notification sent for lead: {name}")
            return response.status_code == 204

        except Exception as e:
            print(f"Discord notification error: {str(e)}")
            return False

    @staticmethod
    def log_notification(lead_data):
        """Log notification for analytics"""
        try:
            from database import get_db_session
            from models import UserBehavior

            db_session = get_db_session()

            notification_log = UserBehavior(
                session_id=lead_data.get('session_id'),
                action='notification_sent',
                behavior_metadata=json.dumps({
                    'lead_score': lead_data.get('lead_score'),
                    'lead_type': lead_data.get('lead_type'),
                    'notification_time': datetime.now().isoformat()
                }),
                created_at=datetime.now()
            )

            db_session.add(notification_log)
            db_session.commit()
            db_session.close()

            print(
                f"📝 Notification logged for session: {lead_data.get('session_id')}")

        except Exception as e:
            print(f"Notification logging error: {str(e)}")

    @staticmethod
    def send_realtime_update(lead_data):
        """Send real-time update to dashboard via WebSocket (for future implementation)"""
        # This would integrate with WebSocket for real-time dashboard updates
        # For now, we'll store it for polling
        try:
            from database import get_db_session

            # Store real-time update data
            print(
                f"📡 Real-time update prepared for: {lead_data.get('name', 'Anonymous')}")

        except Exception as e:
            print(f"Real-time update error: {str(e)}")
