import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'SQLALCHEMY_DATABASE_URI')
    DEBUG = True

    # Notification Settings
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'leads@youshop.com')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'your_app_password')
    SALES_TEAM_EMAILS = os.getenv(
        'SALES_TEAM_EMAILS', 'sales@youshop.com,manager@youshop.com').split(',')

    # Webhook URLs for real-time notifications
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', None)
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', None)
    TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL', None)

    # A/B Testing Configuration
    AB_TESTING_ENABLED = os.getenv(
        'AB_TESTING_ENABLED', 'True').lower() == 'true'

    # Analytics Configuration
    ANALYTICS_RETENTION_DAYS = int(os.getenv('ANALYTICS_RETENTION_DAYS', 90))
    REALTIME_UPDATES_INTERVAL = int(
        os.getenv('REALTIME_UPDATES_INTERVAL', 30))  # seconds
