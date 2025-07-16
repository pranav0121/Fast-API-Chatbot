import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

class Config:
    # Database configuration - MSSQL ONLY
    DB_SERVER = os.getenv('DB_SERVER', 'PRANAV\\SQLEXPRESS')
    DB_DATABASE = os.getenv('DB_DATABASE', 'SupportChatbot')
    DB_USERNAME = os.getenv('DB_USERNAME', 'sa')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_USE_WINDOWS_AUTH = os.getenv('DB_USE_WINDOWS_AUTH', 'True').lower() in ('true', '1', 't')
    
    # SQL Server connection string - NO FALLBACK, MSSQL ONLY
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        # Try multiple SQL Server drivers in order of preference
        drivers_to_try = [
            'ODBC Driver 17 for SQL Server',
            'ODBC Driver 13 for SQL Server',
            'ODBC Driver 11 for SQL Server',
            'SQL Server Native Client 11.0',
            'SQL Server'
        ]
        
        if self.DB_USE_WINDOWS_AUTH:
            # Use Windows Authentication
            for driver in drivers_to_try:
                try:
                    driver_encoded = quote_plus(driver)
                    return f'mssql+pyodbc://{self.DB_SERVER}/{self.DB_DATABASE}?driver={driver_encoded}&trusted_connection=yes'
                except:
                    continue
            # If all drivers fail, use the first one anyway
            driver = quote_plus(drivers_to_try[0])
            return f'mssql+pyodbc://{self.DB_SERVER}/{self.DB_DATABASE}?driver={driver}&trusted_connection=yes'
        else:
            # Use SQL Server Authentication
            for driver in drivers_to_try:
                try:
                    driver_encoded = quote_plus(driver)
                    password = quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ''
                    return f'mssql+pyodbc://{self.DB_USERNAME}:{password}@{self.DB_SERVER}/{self.DB_DATABASE}?driver={driver_encoded}'
                except:
                    continue
            # If all drivers fail, use the first one anyway
            driver = quote_plus(drivers_to_try[0])
            password = quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ''
            return f'mssql+pyodbc://{self.DB_USERNAME}:{password}@{self.DB_SERVER}/{self.DB_DATABASE}?driver={driver}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Disable SQL query logging to reduce noise
    
    # Connection pool configuration to prevent timeouts
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_timeout': 120,
        'pool_recycle': 3600,
        'max_overflow': 50,
        'pool_pre_ping': True
    }
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    
    # Application configuration
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
      # API configuration
    API_TITLE = 'Support Chatbot API'
    API_VERSION = 'v1'
    
    # Odoo configuration
    ODOO_URL = os.getenv('ODOO_URL')
    ODOO_DB = os.getenv('ODOO_DB')
    ODOO_USERNAME = os.getenv('ODOO_USERNAME')
    ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')
