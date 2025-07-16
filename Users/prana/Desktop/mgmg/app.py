from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, redirect, session, flash, Blueprint
from config import Config
odoo_bp = Blueprint('odoo_bp', __name__)

ODOO_MODELS = [
    'res.partner', 'helpdesk.ticket', 'sale.order', 'account.move',
    'product.product', 'product.template', 'project.project', 'project.task',
    'stock.picking', 'stock.move', 'hr.employee', 'res.users', 'purchase.order',
    'account.analytic.line', 'hr.leave', 'hr.attendance', 'mrp.production',
    'website.page', 'blog.post', 'crm.lead', 'mailing.contact', 'mailing.list'
]

def odoo_model_endpoint(model):
    def endpoint():
        if not odoo_service:
            return jsonify({'error': 'Odoo service not available'}), 503
        data = request.get_json() or {}
        method = data.get('method', 'search_read')
        args = data.get('args', [[]])
        kwargs = data.get('kwargs', {})
        try:
            result = odoo_service.models.execute_kw(
                odoo_service.db, odoo_service.uid, odoo_service.password,
                model, method, args, kwargs
            )
            return jsonify({'result': result})
        except Exception as e:
            logger.error(f"Odoo {model} API error: {e}")
            return jsonify({'error': str(e)}), 500
    return endpoint

# ...other imports and code...

app = Flask(__name__)
config_obj = Config()
app.config.from_object(config_obj)

# Register Odoo endpoints after app is defined
for model in ODOO_MODELS:
    endpoint_name = f'odoo_{model.replace(".", "_")}'
    route_path = f'/api/odoo/{model.replace(".", "_")}'
    odoo_bp.add_url_rule(
        route_path,
        endpoint=endpoint_name,
        view_func=odoo_model_endpoint(model),
        methods=['POST']
    )
app.register_blueprint(odoo_bp)
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, redirect, session, flash
from flask_login import LoginManager, login_required, current_user, UserMixin
from flask_babel import Babel, _
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import pyodbc
import logging
from config import Config
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
import uuid
from sqlalchemy import text
from sqlalchemy.sql import case
from functools import wraps
import warnings

# Device Tracking Imports
from device_tracker_core import DeviceInfo, DeviceAnalytics

# Odoo Integration
from odoo_service import OdooService

# Location service for country detection
from location_service import location_service

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Helper function to format timestamps with timezone
def format_timestamp_with_tz(dt):
    """Format datetime object to ISO format with UTC timezone indicator"""
    if dt is None:
        return None
    # Ensure the datetime is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

app = Flask(__name__)
config_obj = Config()
app.config.from_object(config_obj)

# Initialize Flask-Babel for i18n with fallback handling
app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # English as default language
app.config['BABEL_SUPPORTED_LOCALES'] = [
    'en', 'es', 'ar', 'hi', 'it', 'ja', 'ko', 'pt', 'ru', 'ur', 'zh'  # All working languages with English first
]
app.config['LANGUAGES'] = {
    'en': 'English',
    'es': 'Español',
    'ar': 'العربية',
    'hi': 'हिन्दी',
    'it': 'Italiano',
    'ja': '日本語',
    'ko': '한국어',
    'pt': 'Português',
    'ru': 'Русский',
    'ur': 'اردو',
    'zh': '中文'
}
babel = Babel(app)

# Initialize Odoo Service
odoo_service = None
try:
    if hasattr(config_obj, 'ODOO_URL') and config_obj.ODOO_URL:
        odoo_service = OdooService(
            url=config_obj.ODOO_URL,
            db=config_obj.ODOO_DB,
            username=config_obj.ODOO_USERNAME,
            password=config_obj.ODOO_PASSWORD
        )
        logger.info("Odoo service initialized successfully")
    else:
        logger.warning("Odoo configuration not found - Odoo features will be disabled")
except Exception as e:
    logger.error(f"Failed to initialize Odoo service: {e}")
    odoo_service = None

# Add error handling for translation loading
@app.errorhandler(UnicodeDecodeError)
def handle_unicode_error(error):
    """Handle Unicode decode errors in translation files"""
    logger.error(f"Unicode decode error in translations: {str(error)}")
    # Redirect to Spanish (known working language) with error message
    return redirect(url_for('index', lang='es', _error='translation'))

def get_available_languages():
    """Return only languages with properly working translation files"""
    # Include English plus languages that we know have working .mo files (>1000 bytes)
    working_languages = ['en', 'ar', 'es', 'hi', 'it', 'ja', 'ko', 'pt', 'ru', 'ur', 'zh']
    
    # Verify they exist and have substantial content
    translations_dir = os.path.join(app.root_path, 'translations')
    verified_langs = []
    
    if os.path.exists(translations_dir):
        for lang_code in working_languages:
            mo_file = os.path.join(translations_dir, lang_code, 'LC_MESSAGES', 'messages.mo')
            if os.path.exists(mo_file):
                try:
                    # Only include languages with substantial .mo files (actual translations)
                    if os.path.getsize(mo_file) > 500:  # Files with real translations
                        verified_langs.append(lang_code)
                except OSError:
                    continue
    
    # Always include English as the core language
    if 'en' not in verified_langs:
        verified_langs.append('en')
    
    return sorted(verified_langs)

@app.context_processor
def inject_conf_var():
    # Inject available languages and locale into template context
    return dict(
        available_languages=get_available_languages(),
        get_locale=get_locale
    )

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

# Add error handlers for authentication
@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for('auth.login'))

# Handle unauthorized access
@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('auth.login'))

# Babel locale selector with error handling
@babel.localeselector
def get_locale():
    # Check URL parameter first
    requested_lang = request.args.get('lang')
    available_langs = get_available_languages()
    
    if requested_lang and requested_lang in available_langs:
        return requested_lang
    
    # Use user's preferred language if authenticated and available
    if current_user.is_authenticated and hasattr(current_user, 'PreferredLanguage') and current_user.PreferredLanguage:
        if current_user.PreferredLanguage in available_langs:
            return current_user.PreferredLanguage
    
    # Fallback to best match from available languages, default to English
    if available_langs:
        best_match = request.accept_languages.best_match(available_langs)
        return best_match if best_match else ('en' if 'en' in available_langs else available_langs[0])
    else:
        return 'en'  # Ultimate fallback to English

@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    # Change user preferred language
    available_langs = get_available_languages()
    if lang_code in available_langs:
        if current_user.is_authenticated:
            # Save to user profile for authenticated users
            current_user.PreferredLanguage = lang_code
            try:
                db.session.commit()
            except:
                db.session.rollback()
        
        # Redirect with language parameter for session-based language switching
        referrer = request.referrer or url_for('index')
        
        # Parse the URL and update/add the lang parameter properly
        parsed_url = urlparse(referrer)
        query_params = parse_qs(parsed_url.query)
        
        # Update or add the lang parameter
        query_params['lang'] = [lang_code]
        
        # Reconstruct the URL with updated parameters
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return redirect(new_url)
    
    return redirect(request.referrer or url_for('index'))

# Enhanced database connection - MSSQL ONLY
def setup_database():
    """Setup database connection - MSSQL ONLY, no fallback"""
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = config_obj.SQLALCHEMY_DATABASE_URI
        logger.info(f"Database URI configured for MSSQL: {config_obj.SQLALCHEMY_DATABASE_URI}")
        return True
    except Exception as e:
        logger.error(f"Failed to configure MSSQL database URI: {e}")
        logger.error("NO FALLBACK - MSSQL ONLY MODE")
        return False

# Setup database - MSSQL ONLY
if not setup_database():
    logger.critical("MSSQL database setup failed - NO FALLBACK")
    logger.critical("Please ensure MSSQL Server is running and accessible")
    exit(1)

# Configure Flask-SocketIO - use default threading mode
from flask_socketio import SocketIO, emit, join_room, leave_room
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
db = SQLAlchemy(app)

# Database Models - Define all models before using them
class User(UserMixin, db.Model):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(255), unique=True, nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)
    OrganizationName = db.Column(db.String(200), nullable=False)
    Position = db.Column(db.String(100), nullable=True)
    PriorityLevel = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    Phone = db.Column(db.String(20), nullable=True)
    Department = db.Column(db.String(100), nullable=True)
    PreferredLanguage = db.Column(db.String(10), default='en')
    Country = db.Column(db.String(100), nullable=True)  # User's country location
    IsActive = db.Column(db.Boolean, default=True)
    IsAdmin = db.Column(db.Boolean, default=False)
    LastLogin = db.Column(db.DateTime, nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Device Tracking fields
    device_type = db.Column(db.String(20), nullable=True)  # desktop, mobile, tablet
    operating_system = db.Column(db.String(50), nullable=True)  # Windows, macOS, Android, iOS
    browser = db.Column(db.String(50), nullable=True)  # Chrome, Firefox, Safari, Edge
    browser_version = db.Column(db.String(50), nullable=True)  # Browser version string
    os_version = db.Column(db.String(50), nullable=True)  # OS version string
    device_brand = db.Column(db.String(50), nullable=True)  # Apple, Samsung, etc.
    device_model = db.Column(db.String(50), nullable=True)  # iPhone 12, Galaxy S21, etc.
    device_fingerprint = db.Column(db.String(255), nullable=True)  # Unique device identifier
    user_agent = db.Column(db.Text, nullable=True)  # Full user agent string
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6 address

    def get_id(self):
        return str(self.UserID)
    
    def get_priority_weight(self):
        """Return numeric weight for priority sorting"""
        priority_weights = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_weights.get(self.PriorityLevel, 2)

class Category(db.Model):
    __tablename__ = 'Categories'
    CategoryID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50), nullable=False)
    Team = db.Column(db.String(50), nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class Ticket(db.Model):
    __tablename__ = 'Tickets'
    TicketID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'))
    CategoryID = db.Column(db.Integer, db.ForeignKey('Categories.CategoryID'))
    Subject = db.Column(db.String(255), nullable=False)
    Priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    Status = db.Column(db.String(20), default='open')
    OrganizationName = db.Column(db.String(200), nullable=True)  # Cached from user for easier admin viewing
    CreatedBy = db.Column(db.String(100), nullable=True)  # Cached user name for easier admin viewing
    AssignedTo = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=True)  # Admin who handles this
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    EndDate = db.Column(db.DateTime, nullable=True)  # When ticket was actually resolved/closed
    Country = db.Column(db.String(100), nullable=True)  # Country where ticket originated
    EscalationLevel = db.Column(db.String(20), default='normal')  # normal, supervisor, admin escalation levels
    
    # Enhanced Escalation Fields
    EscalationReason = db.Column(db.String(500), nullable=True)  # Reason for escalation
    EscalationTimestamp = db.Column(db.DateTime, nullable=True)  # When ticket was escalated
    EscalatedTo = db.Column(db.String(100), nullable=True)  # Role/person ticket was escalated to
    SLABreachStatus = db.Column(db.String(50), default='Within SLA')  # Within SLA, Approaching Breach, Breached
    AutoEscalated = db.Column(db.Boolean, default=False)  # Whether escalation was automatic
    EscalationHistory = db.Column(db.Text, nullable=True)  # JSON history of escalations
    CurrentAssignedRole = db.Column(db.String(50), default='bot')  # Currently assigned role
    SLATarget = db.Column(db.DateTime, nullable=True)  # Target SLA completion time
    OriginalSLATarget = db.Column(db.DateTime, nullable=True)  # Original SLA target (before escalations)
    
    # Extended Ticket model fields for enterprise features
    escalation_level = db.Column(db.Integer, default=0)  # 0=Bot, 1=ICP, 2=YouCloud  
    current_sla_target = db.Column(db.DateTime, nullable=True)
    resolution_method = db.Column(db.String(50), nullable=True)  # Bot, ICP, YouCloud
    bot_attempted = db.Column(db.Boolean, default=False)
    partner_id = db.Column(db.Integer, nullable=True)  # Will add FK later
    
    # Odoo Integration fields
    odoo_customer_id = db.Column(db.Integer, nullable=True)  # Odoo partner ID
    odoo_ticket_id = db.Column(db.Integer, nullable=True)  # Odoo helpdesk ticket ID
    
    # Device Tracking fields
    device_type = db.Column(db.String(20), nullable=True)  # desktop, mobile, tablet
    operating_system = db.Column(db.String(50), nullable=True)  # Windows, macOS, Android, iOS
    browser = db.Column(db.String(50), nullable=True)  # Chrome, Firefox, Safari, Edge
    browser_version = db.Column(db.String(50), nullable=True)  # Browser version string
    os_version = db.Column(db.String(50), nullable=True)  # OS version string
    device_brand = db.Column(db.String(50), nullable=True)  # Apple, Samsung, etc.
    device_model = db.Column(db.String(50), nullable=True)  # iPhone 12, Galaxy S21, etc.
    device_fingerprint = db.Column(db.String(255), nullable=True)  # Unique device identifier
    user_agent = db.Column(db.Text, nullable=True)  # Full user agent string
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6 address

    # Relationships
    user = db.relationship('User', foreign_keys=[UserID], backref='tickets')
    assigned_admin = db.relationship('User', foreign_keys=[AssignedTo], backref='assigned_tickets')
    
    def get_priority_weight(self):
        """Return numeric weight for priority sorting"""
        priority_weights = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_weights.get(self.Priority, 2)

class Message(db.Model):
    __tablename__ = 'Messages'
    MessageID = db.Column(db.Integer, primary_key=True)
    TicketID = db.Column(db.Integer, db.ForeignKey('Tickets.TicketID'))
    SenderID = db.Column(db.Integer, db.ForeignKey('Users.UserID'))
    Content = db.Column(db.Text, nullable=False)
    IsAdminReply = db.Column(db.Boolean, default=False)
    IsBotResponse = db.Column(db.Boolean, default=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class CommonQuery(db.Model):
    __tablename__ = 'CommonQueries'
    QueryID = db.Column(db.Integer, primary_key=True)
    CategoryID = db.Column(db.Integer, db.ForeignKey('Categories.CategoryID'))
    Question = db.Column(db.String(255), nullable=False)
    Solution = db.Column(db.Text, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Feedback(db.Model):
    __tablename__ = 'Feedback'
    FeedbackID = db.Column(db.Integer, primary_key=True)
    TicketID = db.Column(db.Integer, db.ForeignKey('Tickets.TicketID'))
    Rating = db.Column(db.Integer, nullable=False)
    Comment = db.Column(db.Text)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class Attachment(db.Model):
    __tablename__ = 'Attachments'
    AttachmentID = db.Column(db.Integer, primary_key=True)
    MessageID = db.Column(db.Integer, db.ForeignKey('Messages.MessageID'))
    OriginalName = db.Column(db.String(255), nullable=False)
    StoredName = db.Column(db.String(255), nullable=False)
    FileSize = db.Column(db.Integer, nullable=False)
    MimeType = db.Column(db.String(100), nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

# FAQ Models for independent FAQ management system
class FAQCategory(db.Model):
    __tablename__ = 'faq_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    icon = db.Column(db.String(50), default='question-circle')
    color = db.Column(db.String(20), default='#007bff')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FAQ(db.Model):
    __tablename__ = 'faqs'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('faq_categories.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    language_code = db.Column(db.String(5), default='en')
    tags = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='published')  # draft, published, archived
    created_by = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    category = db.relationship('FAQCategory', backref=db.backref('faqs', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_faqs', lazy=True))
    
    @property
    def is_active(self):
        """Helper property to check if FAQ is active (published and not deleted)"""
        return self.status == 'published' and self.deleted_at is None

class Workflow(db.Model):
    __tablename__ = 'workflows'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    config = db.Column(db.Text, nullable=False)  # JSON configuration
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkflowStep(db.Model):
    __tablename__ = 'workflow_steps'
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    step_type = db.Column(db.String(50), nullable=False)  # condition, action, response
    config = db.Column(db.Text, nullable=False)  # JSON configuration
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    workflow = db.relationship('Workflow', backref=db.backref('steps', lazy=True))

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except:
        return None

# SocketIO event handlers for real-time chat
@socketio.on('join_room')
def handle_join_room(data):
    try:
        ticket_id = data.get('ticket_id')
        room = f"ticket_{ticket_id}"
        join_room(room)
        logger.info(f"User joined room: {room}")
        emit('room_joined', {'ticket_id': ticket_id, 'room': room})
    except Exception as e:
        logger.error(f"Error joining room: {e}")

@socketio.on('leave_room')
def handle_leave_room(data):
    try:
        ticket_id = data.get('ticket_id')
        room = f"ticket_{ticket_id}"
        leave_room(room)
        logger.info(f"User left room: {room}")
    except Exception as e:
        logger.error(f"Error leaving room: {e}")

@socketio.on('send_message')
def handle_send_message(data):
    try:
        ticket_id = data.get('ticket_id')
        content = data.get('content')
        is_admin = data.get('is_admin', False)
        sender_id = getattr(current_user, 'UserID', None) if current_user.is_authenticated else None
        
        logger.info(f"📨 Received message for ticket #{ticket_id}: {content[:50]}... (is_admin: {is_admin})")
        
        # Save message to database
        msg = Message(TicketID=ticket_id, SenderID=sender_id,
                      Content=content, IsAdminReply=is_admin)
        db.session.add(msg)
        
        # Update ticket status and timestamp
        ticket = Ticket.query.get(ticket_id)
        if ticket:
            ticket.UpdatedAt = datetime.utcnow()
            if not is_admin and ticket.Status == 'open':
                ticket.Status = 'in_progress'
        
        db.session.commit()
        logger.info(f"✅ Message saved to database with ID: {msg.MessageID}")
        
        # Handle attachments if present
        attachments_info = []
        if data.get('attachments'):
            for att in data.get('attachments'):
                # Link existing Attachment record to this message
                attachment = Attachment.query.get(att.get('id'))
                if attachment:
                    attachment.MessageID = msg.MessageID
                    db.session.add(attachment)
                    attachments_info.append({
                        'id': attachment.AttachmentID,
                        'original_name': attachment.OriginalName,
                        'url': url_for('uploaded_file', filename=attachment.StoredName, _external=False),
                        'file_size': attachment.FileSize,
                        'mime_type': attachment.MimeType
                    })
        
        db.session.commit()
        
        # Prepare message payload
        msg_data = {
            'ticket_id': ticket_id,
            'id': msg.MessageID,
            'content': msg.Content,
            'is_admin': msg.IsAdminReply,
            'created_at': format_timestamp_with_tz(msg.CreatedAt),
            'attachments': attachments_info
        }
        
        # Broadcast to room
        room = f"ticket_{ticket_id}"
        logger.info(f"📡 Broadcasting message to room: {room}")
        emit('new_message', msg_data, room=room)
        
    except Exception as e:
        logger.error(f"❌ Error handling send_message: {e}")
        import traceback
        traceback.print_exc()
        emit('error', {'message': 'Failed to send message'})

# Enhanced session management
@app.teardown_appcontext
def close_db(error):
    """Close database connections after each request"""
    try:
        db.session.remove()
    except Exception as e:
        logger.error(f"Error closing database session: {str(e)}")

@app.teardown_request
def close_db_session(exception):
    """Ensure database session is properly closed"""
    try:
        if exception:
            db.session.rollback()
        db.session.close()
    except Exception as e:
        logger.error(f"Error in teardown_request: {str(e)}")

# Database health check function
def check_database_health():
    """Check if database is accessible and working"""
    try:
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        return True, "Database connection healthy"
    except Exception as e:
        error_msg = f"Database health check failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Register authentication blueprint after models are defined
from auth import auth_bp, admin_required
app.register_blueprint(auth_bp, url_prefix='/auth')

# Register Super Admin Portal Blueprint (after all models are defined)
def register_super_admin_blueprint():
    from super_admin import super_admin_bp
    app.register_blueprint(super_admin_bp)

# Test route for ticket loading
@app.route('/test-tickets')
def test_tickets_page():
    """Test page for ticket loading functionality"""
    return render_template('test_tickets_loading.html')

# Enhanced admin route for backwards compatibility
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard route"""
    return render_template('admin.html')

# Direct routes for login and register (for convenience)
@app.route('/login')
def login_redirect():
    return redirect(url_for('auth.login'))

@app.route('/register')
def register_redirect():
    return redirect(url_for('auth.register'))

@app.route('/logout')
@login_required
def logout():
    from flask_login import logout_user, current_user
    user_name = current_user.Name if current_user.is_authenticated else "User"
    logout_user()
    flash(f'Goodbye {user_name}! You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def user_profile():
    """User profile page"""
    try:
        return render_template('user_profile.html', user=current_user)
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        try:
            # Update user information
            current_user.Name = request.form.get('name', current_user.Name)
            current_user.Position = request.form.get('position', current_user.Position)
            current_user.Department = request.form.get('department', current_user.Department)
            current_user.Phone = request.form.get('phone', current_user.Phone)
            current_user.PreferredLanguage = request.form.get('language', current_user.PreferredLanguage)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
            return redirect(url_for('user_profile'))
    
    return render_template('edit_profile.html', user=current_user)

@app.route('/my-tickets')
@login_required
def my_tickets():
    """User's tickets page"""
    try:
        # Get user's tickets
        user_tickets = Ticket.query.filter_by(UserID=current_user.UserID).order_by(Ticket.CreatedAt.desc()).all()
        
        # Get categories for display
        categories = {cat.CategoryID: cat.Name for cat in Category.query.all()}
        
        return render_template('my_tickets.html', tickets=user_tickets, categories=categories)
    except Exception as e:
        flash(f'Error loading tickets: {str(e)}', 'error')
        return redirect(url_for('index'))

# Routes
@app.route('/test')
def test():
    return jsonify({'status': 'Application is working!', 'message': 'Test route successful'})

@app.route('/template-test')
def template_test():
    try:
        return render_template('simple_test.html')
    except Exception as e:
        return f"Template error: {str(e)}"

@app.route('/')
def index():
    if current_user.is_authenticated:
        try:
            return render_template('index.html')
        except (UnicodeDecodeError, UnicodeError) as e:
            # Handle translation file encoding errors
            logger.error(f"Translation encoding error: {str(e)}")
            # Force fallback to Spanish locale and retry
            try:
                from flask import session
                session['language'] = 'es'
                return redirect(url_for('index', lang='es'))
            except:
                return f"Translation error occurred. Please try refreshing the page."
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            return f"Error loading page: {str(e)}"
    else:
        return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@app.route('/faq')
@login_required
def faq():
    return render_template('faq.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and return bot responses"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        message = data.get('message', '').strip()
        user_id = data.get('user_id', 'anonymous')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Import bot service
        try:
            from bot_service import process_message
            
            # Process the message with the bot
            bot_response = process_message(message, user_id)
            
            return jsonify({
                'response': bot_response,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
            
        except ImportError:
            # Fallback response if bot service is not available
            fallback_responses = [
                "Thank you for your message. Our support team will assist you shortly.",
                "I understand you need help. Let me connect you with a support agent.",
                "Your request has been received. How can I help you today?",
                "I'm here to help! Please describe your issue in more detail.",
                "Thank you for contacting support. What can I assist you with?"
            ]
            
            import random
            response = random.choice(fallback_responses)
            
            return jsonify({
                'response': response,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'fallback'
            })
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Sorry, I encountered an error. Please try again.'
        }), 500

def optimize_image(image_path, max_size=(800, 800), quality=85):
    """Optimize uploaded image to reduce file size"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if larger than max_size
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized version
            img.save(image_path, 'JPEG', quality=quality, optimize=True)
            return True
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return False

def save_file(file):
    """Save uploaded file and return file info"""
    if not file or not allowed_file(file.filename):
        return None
    
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Optimize if it's an image
        if file_ext in {'jpg', 'jpeg', 'png'}:
            optimize_image(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return {
            'original_name': filename,
            'stored_name': unique_filename,
            'file_size': file_size,
            'mime_type': file.mimetype or f'image/{file_ext}',
            'url': url_for('uploaded_file', filename=unique_filename, _external=False)
        }
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return None

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        print("Getting categories...")
        
        # First, ensure the database has categories
        count = Category.query.count()
        print(f"Current category count: {count}")
        
        if count == 0:
            print("No categories found, creating default categories...")
            # Insert default categories if none exist
            default_categories = [
                Category(Name='Payments', Team='Billing'),
                Category(Name='Product Issues', Team='Product'),
                Category(Name='Technical Glitches', Team='Tech'),
                Category(Name='General Inquiries', Team='General')
            ]
            
            for cat in default_categories:
                db.session.add(cat)
            
            try:
                db.session.commit()
                print("Default categories created successfully")
                
                # Add some common queries
                setup_common_queries()
                print("Common queries setup completed")
            except Exception as e:
                print(f"Error creating categories: {e}")
                db.session.rollback()
                return jsonify({"error": "Failed to create categories"}), 500
        
        categories = Category.query.all()
        print(f"Found {len(categories)} categories")
        
        result = [{'id': c.CategoryID, 'name': c.Name} for c in categories]
        print("Categories result:", result)
        
        return jsonify(result)
        
    except Exception as e:
        print("Error in get_categories:", str(e))
        db.session.rollback()
        
        # Return default categories as fallback
        default_result = [
            {'id': 1, 'name': 'Payments'},
            {'id': 2, 'name': 'Product Issues'},
            {'id': 3, 'name': 'Technical Glitches'},
            {'id': 4, 'name': 'General Inquiries'}
        ]
        print("Returning fallback categories")
        return jsonify(default_result)

def setup_common_queries():
    """Setup default common queries for each category"""
    try:
        categories = Category.query.all()
        
        common_queries_data = {
            'Payments': [
                {
                    'question': 'How do I update my payment method?',
                    'solution': 'You can update your payment method by going to Account Settings > Billing > Payment Methods. Click "Add New Method" or "Edit" next to your existing method.'
                },
                {
                    'question': 'Why was my payment declined?',
                    'solution': 'Payment declines can happen due to insufficient funds, expired cards, or bank security measures. Please check with your bank or try a different payment method.'
                },
                {
                    'question': 'How do I get a refund?',
                    'solution': 'Refunds can be requested within 30 days of purchase. Please contact our billing team with your order number and reason for refund.'
                }
            ],
            'Product Issues': [
                {
                    'question': 'The product is not working as expected',
                    'solution': 'Please try refreshing the page or clearing your browser cache. If the issue persists, try using a different browser or device.'
                },
                {
                    'question': 'I can\'t find a specific feature',
                    'solution': 'Our features are organized in the main navigation menu. You can also use the search function or check our help documentation for detailed guides.'
                },
                {
                    'question': 'How do I report a bug?',
                    'solution': 'You can report bugs by clicking the "Report Issue" button in the app or by sending us a detailed description of the problem including steps to reproduce it.'
                }
            ],
            'Technical Glitches': [
                {
                    'question': 'The page won\'t load properly',
                    'solution': 'Try refreshing the page (Ctrl+F5), clearing your browser cache, or disabling browser extensions. If the problem continues, try a different browser.'
                },
                {
                    'question': 'I\'m getting error messages',
                    'solution': 'Please note down the exact error message and try refreshing the page. If it persists, clear your browser cache and cookies, then try again.'
                },
                {
                    'question': 'The app is running slowly',
                    'solution': 'Slow performance can be due to network issues, browser cache, or high server load. Try closing other browser tabs and refreshing the page.'
                }
            ],
            'General Inquiries': [
                {
                    'question': 'How do I contact customer support?',
                    'solution': 'You can reach our support team through this chat, email us at support@company.com, or call our hotline during business hours.'
                },
                {
                    'question': 'What are your business hours?',
                    'solution': 'Our support team is available Monday to Friday, 9 AM to 6 PM EST. Emergency support is available 24/7 for critical issues.'
                },
                {
                    'question': 'How do I create an account?',
                    'solution': 'Click the "Sign Up" button on our homepage, fill in your details, verify your email address, and you\'re ready to get started!'
                }
            ]
        }
        
        for category in categories:
            if category.Name in common_queries_data:
                for query_data in common_queries_data[category.Name]:
                    # Check if query already exists
                    existing = CommonQuery.query.filter_by(
                        CategoryID=category.CategoryID, 
                        Question=query_data['question']
                    ).first()
                    
                    if not existing:
                        query = CommonQuery(
                            CategoryID=category.CategoryID,
                            Question=query_data['question'],
                            Solution=query_data['solution']
                        )
                        db.session.add(query)
        
        db.session.commit()
        print("Common queries setup completed")
        
    except Exception as e:
        print(f"Error setting up common queries: {str(e)}")
        db.session.rollback()

@app.route('/api/common-queries/<int:category_id>', methods=['GET'])
def get_common_queries(category_id):
    queries = CommonQuery.query.filter_by(CategoryID=category_id).all()
    return jsonify([{
        'id': q.QueryID,
        'question': q.Question,
        'solution': q.Solution
    } for q in queries])

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    try:
        logger.info("Creating new ticket...")
        data = request.json
        logger.info(f"Received data: {data}")
        
        if not data:
            logger.error("No data received")
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }, 400)
        
        # Validate required fields
        if not data.get('message'):
            logger.error("Message is required")
            return jsonify({
                'status': 'error',
                'message': 'Message is required'
            }, 400)
        
        # Handle authenticated user vs guest user
        user = None
        if current_user.is_authenticated:
            # Use authenticated user
            user = current_user
            logger.info(f"Using authenticated user: {user.Name} from {user.OrganizationName}")
        else:
            # Create or get guest user (backward compatibility)
            if data.get('name') or data.get('email'):
                try:
                    # Check if user already exists
                    email = data.get('email')
                    if email:
                        user = User.query.filter_by(Email=email).first()
                    
                    if not user:
                        user = User(
                            Name=data.get('name', 'Anonymous'),
                            Email=data.get('email', ''),
                            OrganizationName=data.get('organization', 'Guest Organization'),
                            PriorityLevel=data.get('priority', 'medium')
                        )
                        db.session.add(user)
                        db.session.flush()  # Get the ID without committing
                    logger.info(f"Created/found guest user with ID: {user.UserID}")
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
                    db.session.rollback()
                    return jsonify({
                        'status': 'error',
                        'message': 'Error creating user'
                    }, 500)
        
        # Get category ID - default to 1 if not provided
        category_id = data.get('category_id', 1)
        logger.info(f"Using category_id: {category_id}")
        
        # Determine ticket priority (use user's priority level by default)
        ticket_priority = data.get('priority', user.PriorityLevel if user else 'medium')
        
        # Auto-detect escalation level based on priority
        if ticket_priority == 'critical':
            escalation_level = 'admin'
        elif ticket_priority == 'high':
            escalation_level = 'supervisor'
        else:
            escalation_level = 'normal'
        
        logger.info(f"Auto-assigned escalation level: {escalation_level} (based on priority: {ticket_priority})")
        
        # Auto-detect country from user's location
        ticket_country = 'Unknown'
        try:
            location_info = location_service.detect_country_from_request(request)
            if location_info and location_info.get('country'):
                ticket_country = location_info['country']
                logger.info(f"Auto-detected country for new ticket: {ticket_country}")
            else:
                logger.warning("Could not auto-detect country for new ticket")
        except Exception as e:
            logger.warning(f"Country auto-detection failed: {e}")
        
        # Create ticket with enhanced information
        try:
            # Calculate initial SLA target
            sla_hours = {
                'critical': 1.0,
                'high': 4.0,
                'medium': 8.0,
                'low': 24.0
            }.get(ticket_priority, 8.0)
            
            sla_target = datetime.utcnow() + timedelta(hours=sla_hours)
            
            # Set initial role assignment
            current_role = 'bot'  # All tickets start with bot
            
            ticket = Ticket(
                UserID=user.UserID if user else None,
                CategoryID=category_id,
                Subject=data.get('subject', 'Support Request'),
                Priority=ticket_priority,
                Status='open',
                OrganizationName=user.OrganizationName if user else data.get('organization', 'Unknown'),
                CreatedBy=user.Name if user else data.get('name', 'Anonymous'),
                Country=ticket_country,  # Add country auto-detection
                EscalationLevel=escalation_level,  # Add escalation level auto-detection
                # Enhanced escalation fields
                SLABreachStatus='Within SLA',
                AutoEscalated=False,
                CurrentAssignedRole=current_role,
                SLATarget=sla_target,
                OriginalSLATarget=sla_target
            )
            db.session.add(ticket)
            db.session.flush()  # Get the ID without committing
            logger.info(f"Created ticket with ID: {ticket.TicketID}, Priority: {ticket_priority}, SLA Target: {sla_target}, Organization: {ticket.OrganizationName}")
        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error creating ticket'
            }, 500)
        
        # Create initial message
        try:
            message = Message(
                TicketID=ticket.TicketID,
                SenderID=user.UserID if user else None,
                Content=data['message'],
                IsAdminReply=False
            )
            db.session.add(message)
            db.session.flush()  # Get message ID without committing
            logger.info(f"Created message with ID: {message.MessageID}")
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error creating message'
            }, 500)
        # Try bot response first (Level 0 automation)
        bot_response = None
        bot_attempted = False
        try:
            bot_response = bot_service.process_query(data['message'], ticket.TicketID)
            bot_attempted = True
            
            if bot_response and bot_response.get('confidence', 0) >= 0.7:
                # Bot provided a confident response
                bot_message = Message(
                    TicketID=ticket.TicketID,
                    SenderID=None,  # Bot response
                    Content=bot_response['response'],
                    IsAdminReply=True,
                    IsBotResponse=True
                )
                db.session.add(bot_message)
                ticket.bot_attempted = True
                ticket.resolution_method = 'bot'
                logger.info(f"Bot provided confident response for ticket {ticket.TicketID}")
            else:
                # Bot response not confident enough, escalate to human
                ticket.bot_attempted = True
                ticket.escalation_level = 1
                ticket.resolution_method = 'human'
                logger.info(f"Bot response not confident enough, escalating ticket {ticket.TicketID} to human")
                
        except Exception as e:
            logger.error(f"Error processing bot response: {str(e)}")
            ticket.bot_attempted = bot_attempted
            ticket.escalation_level = 1
            ticket.resolution_method = 'human'

        # 🔥 NEW: Sync ticket to Odoo Online
        odoo_customer_id = None
        odoo_ticket_id = None
        try:
            if odoo_service:
                logger.info(f"Syncing ticket {ticket.TicketID} to Odoo Online...")
                
                # First, create/find customer in Odoo
                if user and user.Email:
                    try:
                        odoo_customer_id = odoo_service.create_customer(
                            name=user.Name,
                            email=user.Email,
                            comment=f"Organization: {user.OrganizationName}" if user.OrganizationName else None
                        )
                        logger.info(f"Created/found customer in Odoo with ID: {odoo_customer_id}")
                    except Exception as e:
                        logger.warning(f"Could not create customer in Odoo: {e}")
                
                # Create ticket in Odoo
                try:
                    odoo_ticket_id = odoo_service.create_ticket(
                        name=ticket.Subject,
                        description=f"Ticket #{ticket.TicketID} from {ticket.OrganizationName}\n\nMessage: {data['message']}",
                        partner_id=odoo_customer_id,
                        priority='2' if ticket.Priority == 'high' else '1',  # Odoo priority mapping
                        tag_ids=['chatbot-created']
                    )
                    
                    # Store Odoo IDs for future reference
                    ticket.odoo_customer_id = odoo_customer_id
                    ticket.odoo_ticket_id = odoo_ticket_id
                    
                    logger.info(f"✅ Ticket {ticket.TicketID} synced to Odoo ticket {odoo_ticket_id}")
                    
                except Exception as e:
                    logger.warning(f"Could not create ticket in Odoo: {e}")
            else:
                logger.warning("Odoo service not available for ticket sync")
                
        except Exception as e:
            logger.error(f"Error syncing ticket to Odoo: {e}")
            # Don't fail the entire ticket creation if Odoo sync fails

        # Set initial SLA target based on priority and partner
        try:
            sla_monitor.set_initial_sla(ticket)
        except Exception as e:
            logger.error(f"Error setting initial SLA: {str(e)}")
        
        # Capture device tracking information
        try:
            # Extract device info from Flask request
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Create DeviceInfo instance with extracted data
            device_info = DeviceInfo(user_agent_string=user_agent, ip_address=ip_address)
            device_data = device_info.get_complete_info()
            
            # Add device info to ticket
            if device_data:
                browser_info = device_data.get('browser', {})
                os_info = device_data.get('os', {})
                
                ticket.device_type = device_data.get('device_type')
                ticket.operating_system = os_info.get('family') if os_info else None
                ticket.browser = browser_info.get('family') if browser_info else None
                ticket.browser_version = browser_info.get('version_string') if browser_info else None
                ticket.os_version = os_info.get('version_string') if os_info else None
                ticket.device_brand = None  # Not available in simple parser
                ticket.device_model = None  # Not available in simple parser
                ticket.device_fingerprint = f"{device_data.get('device_type')}_{browser_info.get('family', 'unknown')}_{os_info.get('family', 'unknown')}" if browser_info and os_info else None
                ticket.user_agent = device_data.get('user_agent')
                ticket.ip_address = device_data.get('ip_address')
                
                logger.info(f"Device info captured for ticket {ticket.TicketID}: {device_data.get('device_type')} / {browser_info.get('family') if browser_info else 'Unknown'} / {os_info.get('family') if os_info else 'Unknown'}")
            else:
                logger.warning(f"No device data available for ticket {ticket.TicketID}")
        except Exception as e:
            logger.error(f"Device tracking failed for ticket {ticket.TicketID}: {e}")
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Successfully committed ticket {ticket.TicketID}")
        except Exception as e:
            logger.error(f"Error committing ticket: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error saving ticket'
            }, 500)
        
        logger.info(f"Successfully created ticket {ticket.TicketID} for organization {ticket.OrganizationName}")
        
        response_data = {
            'ticket_id': ticket.TicketID,
            'user_id': user.UserID if user else None,
            'priority': ticket.Priority,
            'organization': ticket.OrganizationName,
            'status': 'success',
            'message': 'Ticket created successfully',
            'bot_attempted': bot_attempted,
            'resolution_method': ticket.resolution_method,
            'escalation_level': ticket.escalation_level
        }
        
        if bot_response and bot_response.get('confidence', 0) >= 0.7:
            response_data['bot_response'] = bot_response['response']
            response_data['bot_confidence'] = bot_response['confidence']
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in create_ticket: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }, 500)

@app.route('/api/tickets/<int:ticket_id>/messages', methods=['GET', 'POST'])
def handle_messages(ticket_id):
    if request.method == 'GET':
        messages = Message.query.filter_by(TicketID=ticket_id).order_by(Message.CreatedAt).all()
        message_list = []
        
        for m in messages:
            # Get attachments for this message
            attachments = Attachment.query.filter_by(MessageID=m.MessageID).all()
            
            message_data = {
                'id': m.MessageID,                'content': m.Content,
                'is_admin': m.IsAdminReply,
                'created_at': format_timestamp_with_tz(m.CreatedAt),
                'attachments': [{
                    'id': att.AttachmentID,
                    'original_name': att.OriginalName,
                    'url': f'/static/uploads/{att.StoredName}',
                    'file_size': att.FileSize,
                    'mime_type': att.MimeType
                } for att in attachments]
            }
            message_list.append(message_data)
        
        return jsonify(message_list)
    
    # POST new message
    data = request.json
    message = Message(
        TicketID=ticket_id,
        SenderID=data.get('user_id'),
        Content=data['content'],
        IsAdminReply=data.get('is_admin', False)
    )
    db.session.add(message)
      # Update ticket timestamp
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        ticket.UpdatedAt = datetime.utcnow()
        if data.get('is_admin', False) and ticket.Status == 'open':
            ticket.Status = 'in_progress'
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message_id': message.MessageID
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Save file
        file_info = save_file(file)
        if not file_info:
            return jsonify({'error': 'Failed to save file'}), 500
        
        return jsonify({
            'status': 'success',
            'file_info': file_info
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/tickets/with-attachment', methods=['POST'])
def create_ticket_with_attachment():
    """Create ticket with file attachment"""
    try:
        # Get form data
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'category_id': request.form.get('category_id'),
            'subject': request.form.get('subject'),
            'message': request.form.get('message')
        }
        
        # Validate required fields
        if not all([data['name'], data['email'], data['category_id'], data['message']]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create or get user
        user = User.query.filter_by(Email=data['email']).first()
        if not user:
            # Auto-detect country for new user
            user_country = 'Unknown'
            try:
                location_info = location_service.detect_country_from_request(request)
                if location_info and location_info.get('country'):
                    user_country = location_info['country']
                    logger.info(f"Auto-detected country for new user: {user_country}")
            except Exception as e:
                logger.warning(f"User country auto-detection failed: {e}")
            
            user = User(
                Name=data['name'], 
                Email=data['email'],
                OrganizationName=data.get('organization', 'Unknown'),
                Country=user_country  # Add country auto-detection for new users
            )
            db.session.add(user)
            db.session.flush()
        
        # Auto-detect country for ticket
        ticket_country = 'Unknown'
        try:
            location_info = location_service.detect_country_from_request(request)
            if location_info and location_info.get('country'):
                ticket_country = location_info['country']
                logger.info(f"Auto-detected country for new ticket: {ticket_country}")
        except Exception as e:
            logger.warning(f"Ticket country auto-detection failed: {e}")
        
        # Create ticket
        ticket = Ticket(
            UserID=user.UserID,
            CategoryID=int(data['category_id']),
            Subject=data.get('subject', 'Support Request'),
            Status='open',
            Country=ticket_country  # Add country auto-detection
        )
        db.session.add(ticket)
        db.session.flush()
        
        # Create message
        message = Message(
            TicketID=ticket.TicketID,
            SenderID=user.UserID,
            Content=data['message'],
            IsAdminReply=False
        )
        db.session.add(message)
        db.session.flush()
        
        # Handle file attachment if present
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if allowed_file(file.filename):
                file_info = save_file(file)
                if file_info:
                    attachment = Attachment(
                        MessageID=message.MessageID,
                        OriginalName=file_info['original_name'],
                        StoredName=file_info['stored_name'],
                        FileSize=file_info['file_size'],
                        MimeType=file_info['mime_type']                    )
                    db.session.add(attachment)
        
        db.session.commit()
        
        return jsonify({
            'ticket_id': ticket.TicketID,
            'user_id': user.UserID if user else None,
            'status': 'success',
            'message': 'Ticket created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating ticket with attachment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create ticket'}), 500

@app.route('/api/tickets/<int:ticket_id>/messages/with-attachment', methods=['POST'])
def add_message_with_attachment(ticket_id):
    """Add message to existing ticket with optional attachment"""
    try:
        # Get form data
        content = request.form.get('content')
        user_id = request.form.get('user_id')
        is_admin = request.form.get('is_admin', 'false').lower() == 'true'
        
        if not content:
            return jsonify({'error': 'Message content required'}), 400
        
        # Create message
        message = Message(
            TicketID=ticket_id,
            SenderID=int(user_id) if user_id else None,
            Content=content,
            IsAdminReply=is_admin
        )
        db.session.add(message)
        db.session.flush()
        
        # Handle file attachment if present
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if allowed_file(file.filename):
                file_info = save_file(file)
                if file_info:
                    attachment = Attachment(
                        MessageID=message.MessageID,
                        OriginalName=file_info['original_name'],
                        StoredName=file_info['stored_name'],
                        FileSize=file_info['file_size'],
                        MimeType=file_info['mime_type']
                    )
                    db.session.add(attachment)
        
        # Update ticket timestamp
        ticket = Ticket.query.get(ticket_id)
        if ticket:
            ticket.UpdatedAt = datetime.utcnow()
            if is_admin and ticket.Status == 'open':
                ticket.Status = 'in_progress'
        
        db.session.commit();
        
        return jsonify({
            'status': 'success',
            'message_id': message.MessageID
        })
        
    except Exception as e:
        logger.error(f"Error adding message with attachment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add message'}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



@app.route('/debug-admin')
def debug_admin():
    """Debug admin panel"""
    return render_template('debug_admin.html')

@app.route('/api/admin/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    # Support both session-based and token-based authentication
    try:
        from uv_integration import validate_uv_token
        
        # Check for Urban Vyapari token
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if token:
            payload = validate_uv_token(token)
            if not payload:
                return jsonify({"error": "Invalid or expired token"}), 401
            request.uv_admin = payload
        else:
            # Fall back to session-based authentication
            if 'admin_logged_in' not in session:
                return jsonify({"error": "Authentication required", "login_url": "/admin/login"}), 401
    except ImportError:
        # If UV integration not available, use regular admin auth
        if 'admin_logged_in' not in session:
            return jsonify({"error": "Authentication required", "login_url": "/admin/login"}), 401
    
    try:
        logger.info("Loading dashboard stats...")
        
        # Test database connection first
        try:
            db.session.execute(text('SELECT 1'))
            logger.info("Database connection successful")
        except Exception as db_error:
            logger.error(f"Database connection failed: {str(db_error)}")
            return jsonify({
                "error": "Database connection failed",
                "details": str(db_error)
            }), 500
        
        # Get stats with detailed logging
        total_tickets = Ticket.query.count()
        logger.info(f"Total tickets: {total_tickets}")
        
        pending_tickets = Ticket.query.filter(Ticket.Status.in_(['open', 'in_progress'])).count()
        logger.info(f"Pending tickets: {pending_tickets}")
        
        resolved_tickets = Ticket.query.filter_by(Status='resolved').count()
        logger.info(f"Resolved tickets: {resolved_tickets}")
        
        active_chats = Ticket.query.filter(Ticket.Status.in_(['open', 'in_progress'])).count()
        logger.info(f"Active chats: {active_chats}")
        
        # Also get some sample tickets for debugging
        sample_tickets = Ticket.query.limit(5).all()
        logger.info(f"Sample tickets found: {len(sample_tickets)}")
        for ticket in sample_tickets:
            logger.info(f"Ticket {ticket.TicketID}: {ticket.Subject} - Status: {ticket.Status}")
        
        result = {
            'totalTickets': total_tickets,
            'pendingTickets': pending_tickets,
            'resolvedTickets': resolved_tickets,
            'activeChats': active_chats,
            'success': True
        }
        
        # Add Urban Vyapari metadata if accessed via token
        if hasattr(request, 'uv_admin'):
            result['uv_metadata'] = {
                'accessed_by': request.uv_admin['admin_name'],
                'source': 'urbanvyapari',
                'timestamp': datetime.utcnow().isoformat(),
                'admin_id': request.uv_admin['admin_id']
            }
            logger.info(f"Urban Vyapari dashboard access by: {request.uv_admin['admin_name']}")
        
        logger.info(f"Dashboard stats result: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in get_dashboard_stats: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e),
            "message": "Failed to load dashboard statistics"
        }), 500

@app.route('/api/admin/recent-activity', methods=['GET'])
@admin_required
def get_recent_activity():
    try:
        # Get recent tickets and messages
        recent_tickets = db.session.query(Ticket, User, Category).join(
            User, Ticket.UserID == User.UserID, isouter=True
        ).join(
            Category, Ticket.CategoryID == Category.CategoryID        ).order_by(Ticket.CreatedAt.desc()).limit(10).all()
        
        activities = []
        for ticket, user, category in recent_tickets:
            activities.append({
                'icon': 'fas fa-ticket-alt',
                'title': f'New ticket #{ticket.TicketID}',
                'description': f'{category.Name} - {user.Name if user else "Anonymous"}',
                'created_at': format_timestamp_with_tz(ticket.CreatedAt)
            })
        
        return jsonify(activities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/tickets', methods=['GET'])
def get_admin_tickets():
    # Support both session-based and token-based authentication
    try:
        from uv_integration import validate_uv_token
        
        # Check for Urban Vyapari token
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if token:
            payload = validate_uv_token(token)
            if not payload:
                return jsonify({"error": "Invalid or expired token"}), 401
            request.uv_admin = payload
        else:
            # Fall back to session-based authentication
            if 'admin_logged_in' not in session:
                return jsonify({"error": "Authentication required", "login_url": "/admin/login"}), 401
    except ImportError:
        # If UV integration not available, use regular admin auth
        if 'admin_logged_in' not in session:
            return jsonify({"error": "Authentication required", "login_url": "/admin/login"}), 401
    
    try:
        logger.info("Loading admin tickets...")
        
        # Apply query filters for Urban Vyapari integration
        try:
            from uv_integration import apply_query_filters
            filters = apply_query_filters(request.args)
            logger.info(f"Applied filters: {filters}")
        except:
            filters = {'status': 'all', 'priority': 'all', 'category': 'all', 'limit': 50, 'offset': 0}
        
        # Ensure tables exist first
        try:
            db.create_all()
            logger.info("Database tables created/verified")
        except Exception as table_error:
            logger.error(f"Error creating tables: {str(table_error)}")
        
        # Test database connection
        try:
            db.session.execute(text('SELECT 1'))
            logger.info("Database connection successful for tickets")
        except Exception as db_error:
            logger.error(f"Database connection failed in tickets: {str(db_error)}")
            return jsonify({
                "error": "Database connection failed",
                "details": str(db_error)
            }), 500
        
        # Try simple query first to check if Ticket table exists
        try:
            ticket_count = db.session.query(Ticket).count()
            logger.info(f"Found {ticket_count} tickets in database")
            
            if ticket_count == 0:
                logger.info("No tickets found, returning empty response")
                return jsonify({
                    'success': True,
                    'tickets': [],
                    'pagination': {
                        'total': 0,
                        'limit': filters['limit'],
                        'offset': filters['offset'],
                        'has_more': False
                    },
                    'filters': {
                        'status': filters['status'],
                        'priority': filters['priority'],
                        'category': filters['category']
                    }
                })
            
        except Exception as count_error:
            logger.error(f"Error counting tickets: {str(count_error)}")
            # Table might not exist, return empty response
            return jsonify({
                'success': True,
                'tickets': [],
                'pagination': {
                    'total': 0,
                    'limit': filters['limit'],
                    'offset': filters['offset'],
                    'has_more': False
                },
                'filters': {
                    'status': filters['status'],
                    'priority': filters['priority'],
                    'category': filters['category']
                }
            })
        
        # Try to get tickets with detailed logging and priority sorting
        try:
            tickets = db.session.query(Ticket, User, Category).join(
                User, Ticket.UserID == User.UserID, isouter=True
            ).join(
                Category, Ticket.CategoryID == Category.CategoryID, isouter=True
            ).order_by(
                # Sort by priority first (critical -> high -> medium -> low), then by created date
                case(
                    (Ticket.Priority == 'critical', 4),
                    (Ticket.Priority == 'high', 3),
                    (Ticket.Priority == 'medium', 2),
                    (Ticket.Priority == 'low', 1),
                    else_=2
                ).desc(),
                Ticket.CreatedAt.desc()            ).all()
            
            logger.info(f"Found {len(tickets)} tickets in database")
            
            result = []
            for ticket, user, category in tickets:
                ticket_data = {
                    'id': ticket.TicketID,
                    'subject': ticket.Subject,
                    'category': category.Name if category else 'Unknown',
                    'user_name': user.Name if user else ticket.CreatedBy or 'Anonymous',
                    'user_email': user.Email if user else 'No email',
                    'organization': user.OrganizationName if user else ticket.OrganizationName or 'Unknown Organization',
                    'priority': ticket.Priority or 'medium',
                    'escalation_level': ticket.EscalationLevel or 'normal',  # Add escalation level
                    'escalation_reason': ticket.EscalationReason,  # Enhanced escalation info
                    'escalated_to': ticket.EscalatedTo,
                    'auto_escalated': ticket.AutoEscalated or False,
                    'sla_breach_status': ticket.SLABreachStatus or 'Within SLA',
                    'current_assigned_role': ticket.CurrentAssignedRole or 'bot',
                    'sla_target': format_timestamp_with_tz(ticket.SLATarget) if ticket.SLATarget else None,
                    'status': ticket.Status,
                    'created_at': format_timestamp_with_tz(ticket.CreatedAt),
                    'updated_at': format_timestamp_with_tz(ticket.UpdatedAt) if ticket.UpdatedAt else format_timestamp_with_tz(ticket.CreatedAt),
                    'end_date': format_timestamp_with_tz(ticket.EndDate) if ticket.EndDate else None,
                    'country': ticket.Country if ticket.Country else 'Unknown'  # Add country information
                }
                result.append(ticket_data)
                logger.info(f"Processed ticket {ticket.TicketID}: {ticket.Subject} - Priority: {ticket.Priority}, Org: {ticket_data['organization']}")
            
            logger.info(f"Returning {len(result)} tickets to admin panel sorted by priority")
            
            # Apply filters if using Urban Vyapari integration
            if filters['status'] != 'all':
                result = [t for t in result if t['status'] == filters['status']]
            if filters['priority'] != 'all':
                result = [t for t in result if t['priority'] == filters['priority']]
            if filters['category'] != 'all' and filters['category'] != 'Unknown':
                result = [t for t in result if t['category'].lower() == filters['category'].lower()]
            
            # Apply pagination
            total_count = len(result)
            start_idx = filters['offset']
            end_idx = start_idx + filters['limit']
            paginated_result = result[start_idx:end_idx]
            
            # Always return consistent dictionary format
            response_data = {
                'success': True,
                'tickets': paginated_result,
                'pagination': {
                    'total': total_count,
                    'limit': filters['limit'],
                    'offset': filters['offset'],
                    'has_more': end_idx < total_count
                },
                'filters': {
                    'status': filters['status'],
                    'priority': filters['priority'],
                    'category': filters['category']
                }
            }
            
            # Add Urban Vyapari metadata if accessed via token
            if hasattr(request, 'uv_admin'):
                response_data['uv_metadata'] = {
                    'accessed_by': request.uv_admin['admin_name'],
                    'source': 'urbanvyapari',
                    'timestamp': datetime.utcnow().isoformat(),
                    'admin_id': request.uv_admin['admin_id']
                }
                logger.info(f"Urban Vyapari access by: {request.uv_admin['admin_name']}")
            
            return jsonify(response_data)
            
        except Exception as query_error:
            logger.error(f"Error querying tickets with joins: {str(query_error)}", exc_info=True)
            
            # Try a simpler query as fallback
            try:
                simple_tickets = Ticket.query.all()
                logger.info(f"Fallback: Found {len(simple_tickets)} tickets with simple query")
                
                result = []
                for ticket in simple_tickets:
                    result.append({
                        'id': ticket.TicketID,
                        'subject': ticket.Subject,
                        'category': 'Unknown',
                        'user_name': ticket.CreatedBy or 'Unknown',
                        'user_email': 'Unknown',
                        'organization': ticket.OrganizationName or 'Unknown Organization',
                        'priority': ticket.Priority or 'medium',
                        'status': ticket.Status,                        'created_at': format_timestamp_with_tz(ticket.CreatedAt),
                        'updated_at': format_timestamp_with_tz(ticket.UpdatedAt) if ticket.UpdatedAt else format_timestamp_with_tz(ticket.CreatedAt),
                        'end_date': format_timestamp_with_tz(ticket.EndDate) if ticket.EndDate else None
                    })
                
                # Apply filters if using Urban Vyapari integration
                if filters['status'] != 'all':
                    result = [t for t in result if t['status'] == filters['status']]
                if filters['priority'] != 'all':
                    result = [t for t in result if t['priority'] == filters['priority']]
                if filters['category'] != 'all' and filters['category'] != 'Unknown':
                    result = [t for t in result if t['category'].lower() == filters['category'].lower()]
                
                # Apply pagination
                total_count = len(result)
                start_idx = filters['offset']
                end_idx = start_idx + filters['limit']
                result = result[start_idx:end_idx]
                
                # Enhance response for Urban Vyapari
                response_data = {
                    'success': True,
                    'tickets': result,
                    'pagination': {
                        'total': total_count,
                        'limit': filters['limit'],
                        'offset': filters['offset'],
                        'has_more': end_idx < total_count
                    },
                    'filters': {
                        'status': filters['status'],
                        'priority': filters['priority'],
                        'category': filters['category']
                    }
                }
                
                # Add Urban Vyapari metadata if accessed via token
                if hasattr(request, 'uv_admin'):
                    response_data['uv_metadata'] = {
                        'accessed_by': request.uv_admin['admin_name'],
                        'source': 'urbanvyapari',
                        'timestamp': datetime.utcnow().isoformat(),
                        'admin_id': request.uv_admin['admin_id']
                    }
                    logger.info(f"Urban Vyapari access by: {request.uv_admin['admin_name']}")
                
                return jsonify(response_data)
                
            except Exception as simple_error:
                logger.error(f"Even simple query failed: {str(simple_error)}")
                return jsonify({
                    'success': True,
                    'tickets': [],
                    'pagination': {
                        'total': 0,
                        'limit': filters['limit'],
                        'offset': filters['offset'],
                        'has_more': False
                    },
                    'filters': {
                        'status': filters['status'],
                        'priority': filters['priority'],
                        'category': filters['category']
                    }
                })
        
    except Exception as e:
        logger.error(f"Unexpected error in get_admin_tickets: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch tickets',
            'tickets': [],
            'pagination': {
                'total': 0,
                'limit': 50,
                'offset': 0,
                'has_more': False
            }
        })

@app.route('/api/admin/tickets/<int:ticket_id>', methods=['GET'])
@admin_required
def get_admin_ticket_details(ticket_id):
    try:
        logger.info(f"Loading admin ticket details for ticket ID: {ticket_id}")
        
        ticket = db.session.query(Ticket, User, Category).join(
            User, Ticket.UserID == User.UserID, isouter=True
        ).join(
            Category, Ticket.CategoryID == Category.CategoryID
        ).filter(Ticket.TicketID == ticket_id).first()
        
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return jsonify({"error": "Ticket not found"}), 404
        
        ticket_obj, user, category = ticket
        logger.info(f"Found ticket {ticket_id}: {ticket_obj.Subject}")
        
        # Get messages with attachments
        messages = Message.query.filter_by(TicketID=ticket_id).order_by(Message.CreatedAt).all()
        logger.info(f"Found {len(messages)} messages for ticket {ticket_id}")
        
        # Build message list with attachment information
        message_list = []
        for msg in messages:
            # Get attachments for this message
            attachments = Attachment.query.filter_by(MessageID=msg.MessageID).all()
            logger.info(f"Message {msg.MessageID} has {len(attachments)} attachments")
            
            message_data = {
                'content': msg.Content,
                'is_admin': msg.IsAdminReply,
                'created_at': format_timestamp_with_tz(msg.CreatedAt),
                'attachments': [{
                    'id': att.AttachmentID,
                    'original_name': att.OriginalName,
                    'url': f'/static/uploads/{att.StoredName}',
                    'file_path': f'/static/uploads/{att.StoredName}',
                    'filename': att.StoredName,
                    'file_size': att.FileSize,
                    'mime_type': att.MimeType
                } for att in attachments]
            }
            
            # Add attachment_url for backward compatibility
            if attachments:
                message_data['attachment_url'] = f'/static/uploads/{attachments[0].StoredName}'
                logger.info(f"Added attachment URL: {message_data['attachment_url']}")
            
            message_list.append(message_data)
        
        result = {
            'id': ticket_obj.TicketID,
            'subject': ticket_obj.Subject,
            'category': category.Name,
            'user_name': user.Name if user else None,
            'user_email': user.Email if user else None,
            'priority': ticket_obj.Priority or 'medium',
            'escalation_level': ticket_obj.EscalationLevel or 'normal',  # Add escalation level
            'escalation_reason': ticket_obj.EscalationReason,  # Enhanced escalation info
            'escalated_to': ticket_obj.EscalatedTo,
            'escalation_timestamp': format_timestamp_with_tz(ticket_obj.EscalationTimestamp) if ticket_obj.EscalationTimestamp else None,
            'auto_escalated': ticket_obj.AutoEscalated or False,
            'sla_breach_status': ticket_obj.SLABreachStatus or 'Within SLA',
            'current_assigned_role': ticket_obj.CurrentAssignedRole or 'bot',
            'sla_target': format_timestamp_with_tz(ticket_obj.SLATarget) if ticket_obj.SLATarget else None,
            'original_sla_target': format_timestamp_with_tz(ticket_obj.OriginalSLATarget) if ticket_obj.OriginalSLATarget else None,
            'status': ticket_obj.Status,
            'created_at': format_timestamp_with_tz(ticket_obj.CreatedAt),
            'updated_at': format_timestamp_with_tz(ticket_obj.UpdatedAt) if ticket_obj.UpdatedAt else None,
            'end_date': format_timestamp_with_tz(ticket_obj.EndDate) if ticket_obj.EndDate else None,
            'organization': user.OrganizationName if user else ticket_obj.OrganizationName or 'Unknown Organization',  # Add organization
            'country': ticket_obj.Country if ticket_obj.Country else 'Unknown',  # Add country information
            'messages': message_list
        }
        
        logger.info(f"Returning ticket details for {ticket_id} with {len(message_list)} messages")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting admin ticket details for {ticket_id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/active-conversations', methods=['GET'])
@admin_required
def get_active_conversations():
    try:
        # Get tickets with recent activity
        conversations = db.session.query(Ticket, User, Category).join(
            User, Ticket.UserID == User.UserID, isouter=True
        ).join(
            Category, Ticket.CategoryID == Category.CategoryID
        ).filter(Ticket.Status.in_(['open', 'in_progress', 'escalated'])).order_by(Ticket.UpdatedAt.desc()).all()
        
        result = []
        for ticket, user, category in conversations:
            # Get last message time
            last_message = Message.query.filter_by(TicketID=ticket.TicketID).order_by(Message.CreatedAt.desc()).first()
            
            # Count unread admin messages (assuming we track this)
            unread_count = Message.query.filter_by(TicketID=ticket.TicketID, IsAdminReply=False).count()
            
            result.append({
                'id': ticket.TicketID,
                'subject': ticket.Subject,
                'user_name': user.Name if user else None,
                'category': category.Name,                'status': ticket.Status,
                'last_message_at': format_timestamp_with_tz(last_message.CreatedAt) if last_message else format_timestamp_with_tz(ticket.CreatedAt),
                'unread_count': min(unread_count, 5)  # Cap at 5 for display
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/tickets/<int:ticket_id>/status', methods=['PUT'])
@admin_required
def update_ticket_status(ticket_id):
    try:
        data = request.json
        new_status = data.get('status')
        admin_message = data.get('message', '')  # Optional message from admin
        
        if new_status not in ['open', 'in_progress', 'resolved', 'closed']:
            return jsonify({"error": "Invalid status"}), 400
        
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        
        # Update ticket status
        old_status = ticket.Status
        ticket.Status = new_status
        ticket.UpdatedAt = datetime.utcnow()
        
        # Set EndDate when ticket is resolved or closed
        if new_status in ['resolved', 'closed'] and old_status not in ['resolved', 'closed']:
            ticket.EndDate = datetime.utcnow()
        # Clear EndDate if ticket is reopened from resolved/closed state
        elif old_status in ['resolved', 'closed'] and new_status not in ['resolved', 'closed']:
            ticket.EndDate = None
        
        # If ticket is being resolved or closed, send notification to user
        if new_status in ['resolved', 'closed'] and old_status not in ['resolved', 'closed']:
            # Create a system message to notify the user
            notification_content = admin_message if admin_message else (
                "Your issue has been resolved. Thank you for contacting support! "
                "If you need further assistance, please feel free to create a new ticket."
            )
            
            # Add the notification as an admin message
            notification_message = Message(
                TicketID=ticket_id,
                SenderID=None,  # System message
                Content=notification_content,
                IsAdminReply=True,
                CreatedAt=datetime.utcnow()
            )
            db.session.add(notification_message)
            
            # Also add a system closure message
            if new_status == 'closed':
                closure_message = Message(
                    TicketID=ticket_id,
                    SenderID=None,  # System message
                    Content="This chat session has been closed. Rating and feedback are appreciated.",
                    IsAdminReply=True,
                    CreatedAt=datetime.utcnow()
                )
                db.session.add(closure_message)
        
        db.session.commit()
        
        response_data = {
            "status": "success", 
            "message": "Ticket status updated",
            "new_status": new_status,
            "end_date": format_timestamp_with_tz(ticket.EndDate) if ticket.EndDate else None,
            "notification_sent": new_status in ['resolved', 'closed'] and old_status not in ['resolved', 'closed']
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error updating ticket status: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/analytics', methods=['GET'])
@admin_required
def get_analytics():
    try:
        # Category distribution
        category_stats = db.session.query(Category.Name, db.func.count(Ticket.TicketID)).join(
            Ticket, Category.CategoryID == Ticket.TicketID
        ).group_by(Category.Name).all()
        
        category_data = {
            'labels': [stat[0] for stat in category_stats],
            'values': [stat[1] for stat in category_stats]
        }
        
        # Resolution time (mock data for now)
        resolution_data = {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'values': [2.5, 3.2, 2.8, 4.1, 3.5, 2.1, 1.8]
        }
        
        return jsonify({
            'categoryData': category_data,
            'resolutionData': resolution_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback for a ticket"""
    try:
        data = request.json
        ticket_id = data.get('ticket_id')
        rating = data.get('rating', 0)
        feedback_text = data.get('feedback', '')
        
        if not ticket_id:
            return jsonify({"error": "Ticket ID is required"}), 400
        
        # Verify ticket exists
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        
        # Create feedback message
        feedback_message = Message(
            TicketID=ticket_id,
            SenderID=None,  # System message
            Content=f"User Feedback - Rating: {rating}/5 stars" + 
                   (f"\nFeedback: {feedback_text}" if feedback_text else ""),
            IsAdminReply=False,
            CreatedAt=datetime.utcnow()
        )
        
        db.session.add(feedback_message)
        db.session.commit()
        
        logger.info(f"Feedback submitted for ticket {ticket_id}: Rating={rating}")
        
        return jsonify({
            "status": "success",
            "message": "Thank you for your feedback!"
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    try:
        health_status, health_message = check_database_health()
        
        if health_status:
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "message": health_message,                "timestamp": format_timestamp_with_tz(datetime.utcnow())
            }), 200
        else:
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": health_message,
                "timestamp": format_timestamp_with_tz(datetime.utcnow())
            }), 503
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": format_timestamp_with_tz(datetime.utcnow())
        }), 500

@app.route('/api/database/test', methods=['GET'])
def test_database():
    """Test database operations"""
    try:
        # Test basic connection
        health_status, health_message = check_database_health()
        if not health_status:
            return jsonify({"error": health_message}), 500
        
        # Test table access
        category_count = Category.query.count()
        ticket_count = Ticket.query.count()
        user_count = User.query.count()
        
        return jsonify({
            "status": "success",
            "database": "connected",
            "tables": {
                "categories": category_count,
                "tickets": ticket_count,
                "users": user_count
            },
            "message": "All database operations successful"
        })
        
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket_details(ticket_id):
    """Get ticket details including status and messages for user interface"""
    try:
        # Get ticket with user and category info
        ticket_query = db.session.query(Ticket, User, Category).join(
            User, Ticket.UserID == User.UserID, isouter=True
        ).join(
            Category, Ticket.CategoryID == Category.CategoryID
        ).filter(Ticket.TicketID == ticket_id).first()
        
        if not ticket_query:
            return jsonify({"error": "Ticket not found"}), 404
        
        ticket, user, category = ticket_query
          # Get messages for this ticket
        messages = Message.query.filter_by(TicketID=ticket_id).order_by(Message.CreatedAt).all()
        
        # Build message list with attachments
        message_list = []
        for msg in messages:
            attachments = Attachment.query.filter_by(MessageID=msg.MessageID).all()
            message_data = {
                'content': msg.Content,
                'is_admin': msg.IsAdminReply,
                'created_at': format_timestamp_with_tz(msg.CreatedAt),
                'attachments': [{
                    'id': att.AttachmentID,
                    'original_name': att.OriginalName,
                    'url': f'/static/uploads/{att.StoredName}',
                    'file_size': att.FileSize,
                    'mime_type': att.MimeType
                } for att in attachments]
            }
            message_list.append(message_data)
        
        result = {
            'id': ticket.TicketID,
            'subject': ticket.Subject,
            'status': ticket.Status,
            'category': category.Name if category else 'Unknown',
            'user_name': user.Name if user else 'Anonymous',
            'user_email': user.Email if user else 'No email',
            'created_at': format_timestamp_with_tz(ticket.CreatedAt),
            'updated_at': format_timestamp_with_tz(ticket.UpdatedAt),
            'end_date': format_timestamp_with_tz(ticket.EndDate) if ticket.EndDate else None,
            'country': ticket.Country if ticket.Country else 'Unknown',  # Add country information
            'messages': message_list
        }
        
        logger.info(f"Returning ticket details for {ticket_id}: Status={ticket.Status}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting ticket details: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================================
# ENHANCED ESCALATION API ENDPOINTS
# ============================================================================

@app.route('/api/tickets/<int:ticket_id>/escalate', methods=['POST'])
@admin_required
def escalate_ticket(ticket_id):
    """Escalate a ticket with comprehensive tracking"""
    try:
        data = request.json or {}
        
        # Get the ticket
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        
        # Get escalation parameters
        escalation_reason = data.get('escalationReason', 'Manual escalation')
        escalated_to = data.get('escalatedTo')  # e.g., "supervisor_03", "admin_01"
        auto_escalated = data.get('autoEscalated', False)
        new_escalation_level = data.get('escalationLevel', 1)
        
        # Determine role from escalation level or escalated_to
        if escalated_to:
            if 'supervisor' in escalated_to.lower():
                role = 'supervisor'
                escalation_level = 'supervisor'
            elif 'admin' in escalated_to.lower() or 'manager' in escalated_to.lower():
                role = 'admin'
                escalation_level = 'admin'
            else:
                role = 'supervisor'
                escalation_level = 'supervisor'
        else:
            # Auto-determine based on escalation level
            if new_escalation_level >= 2:
                role = 'admin'
                escalation_level = 'admin'
                escalated_to = 'admin_auto'
            else:
                role = 'supervisor'
                escalation_level = 'supervisor'
                escalated_to = 'supervisor_auto'
        
        # Update ticket escalation fields
        now = datetime.utcnow()
        
        # Create escalation history entry
        import json
        escalation_entry = {
            "ticketId": f"TCK-{ticket_id}",
            "escalationLevel": new_escalation_level,
            "escalatedTo": escalated_to,
            "escalationReason": escalation_reason,
            "escalationTimestamp": now.isoformat() + "Z",
            "autoEscalated": auto_escalated,
            "previousLevel": ticket.EscalationLevel,
            "previousRole": ticket.CurrentAssignedRole or 'bot'
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
        
        # Update ticket fields
        ticket.EscalationLevel = escalation_level
        ticket.EscalationReason = escalation_reason
        ticket.EscalationTimestamp = now
        ticket.EscalatedTo = escalated_to
        ticket.AutoEscalated = auto_escalated
        ticket.EscalationHistory = json.dumps(history)
        ticket.CurrentAssignedRole = role
        ticket.UpdatedAt = now
        
        # Update status if needed
        if ticket.Status == 'open':
            ticket.Status = 'escalated'
        
        db.session.commit()
        
        logger.info(f"Ticket {ticket_id} escalated to {escalation_level} level (role: {role})")
        
        return jsonify({
            "success": True,
            "message": f"Ticket escalated to {escalation_level} level",
            "escalation": escalation_entry,
            "ticket": {
                "id": ticket.TicketID,
                "escalationLevel": ticket.EscalationLevel,
                "escalatedTo": ticket.EscalatedTo,
                "currentAssignedRole": ticket.CurrentAssignedRole,
                "status": ticket.Status,
                "slaBreachStatus": ticket.SLABreachStatus
            }
        })
        
    except Exception as e:
        logger.error(f"Error escalating ticket {ticket_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/tickets/<int:ticket_id>/sla-status', methods=['GET'])
def get_ticket_sla_status(ticket_id):
    """Get detailed SLA status for a ticket"""
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        
        # Calculate SLA status
        now = datetime.utcnow()
        sla_status = "Within SLA"
        time_remaining = None
        sla_percentage = 0
        
        if ticket.SLATarget:
            time_remaining_seconds = (ticket.SLATarget - now).total_seconds()
            
            if ticket.OriginalSLATarget:
                total_sla_seconds = (ticket.SLATarget - ticket.CreatedAt).total_seconds()
                elapsed_seconds = (now - ticket.CreatedAt).total_seconds()
                sla_percentage = min(100, (elapsed_seconds / total_sla_seconds) * 100) if total_sla_seconds > 0 else 0
            
            if time_remaining_seconds <= 0:
                sla_status = "Breached"
            elif time_remaining_seconds <= 3600:  # 1 hour warning
                sla_status = "Approaching Breach"
            else:
                sla_status = "Within SLA"
            
            time_remaining = max(0, time_remaining_seconds)
        
        # Update SLA breach status if it has changed
        if ticket.SLABreachStatus != sla_status:
            ticket.SLABreachStatus = sla_status
            db.session.commit()
        
        return jsonify({
            "ticketId": f"TCK-{ticket.TicketID}",
            "slaBreachStatus": sla_status,
            "slaTarget": ticket.SLATarget.isoformat() + "Z" if ticket.SLATarget else None,
            "originalSlaTarget": ticket.OriginalSLATarget.isoformat() + "Z" if ticket.OriginalSLATarget else None,
            "timeRemainingSeconds": time_remaining,
            "slaPercentageElapsed": round(sla_percentage, 1),
            "priority": ticket.Priority,
            "escalationLevel": ticket.EscalationLevel,
            "currentAssignedRole": ticket.CurrentAssignedRole,
            "autoEscalated": ticket.AutoEscalated or False
        })
        
    except Exception as e:
        logger.error(f"Error getting SLA status for ticket {ticket_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tickets/sla-monitor', methods=['GET'])
@admin_required
def get_sla_monitor_dashboard():
    """Get SLA monitoring dashboard data"""
    try:
        # Get tickets approaching SLA breach
        now = datetime.utcnow()
        approaching_breach = Ticket.query.filter(
            Ticket.Status.in_(['open', 'in_progress', 'escalated']),
            Ticket.SLATarget.isnot(None),
            Ticket.SLATarget > now,
            Ticket.SLATarget <= now + timedelta(hours=2)  # Next 2 hours
        ).all()
        
        # Get breached tickets
        breached = Ticket.query.filter(
            Ticket.Status.in_(['open', 'in_progress', 'escalated']),
            Ticket.SLATarget.isnot(None),
            Ticket.SLATarget <= now
        ).all()
        
        # Get tickets by escalation level
        escalation_stats = db.session.query(
            Ticket.EscalationLevel,
            db.func.count(Ticket.TicketID).label('count')
        ).filter(
            Ticket.Status.in_(['open', 'in_progress', 'escalated'])
        ).group_by(Ticket.EscalationLevel).all()
        
        # Format approaching breach tickets
        approaching_data = []
        for ticket in approaching_breach:
            time_remaining = (ticket.SLATarget - now).total_seconds()
            approaching_data.append({
                "ticketId": f"TCK-{ticket.TicketID}",
                "subject": ticket.Subject,
                "priority": ticket.Priority,
                "escalationLevel": ticket.EscalationLevel,
                "timeRemainingMinutes": round(time_remaining / 60),
                "slaTarget": ticket.SLATarget.isoformat() + "Z"
            })
        
        # Format breached tickets
        breached_data = []
        for ticket in breached:
            time_over = (now - ticket.SLATarget).total_seconds()
            breached_data.append({
                "ticketId": f"TCK-{ticket.TicketID}",
                "subject": ticket.Subject,
                "priority": ticket.Priority,
                "escalationLevel": ticket.EscalationLevel,
                "timeOverMinutes": round(time_over / 60),
                "slaTarget": ticket.SLATarget.isoformat() + "Z"
            })
        
        return jsonify({
            "summary": {
                "approachingBreach": len(approaching_breach),
                "breached": len(breached),
                "escalationLevels": {level: count for level, count in escalation_stats}
            },
            "approachingBreach": approaching_data,
            "breached": breached_data,
            "timestamp": now.isoformat() + "Z"
        })
        
    except Exception as e:
        logger.error(f"Error getting SLA monitor dashboard: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tickets/<int:ticket_id>/escalation-history', methods=['GET'])
def get_ticket_escalation_history(ticket_id):
    """Get escalation history for a ticket"""
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        
        # Parse escalation history
        history = []
        if ticket.EscalationHistory:
            try:
                import json
                history = json.loads(ticket.EscalationHistory)
            except:
                history = []
        
        return jsonify({
            "ticketId": f"TCK-{ticket.TicketID}",
            "currentEscalationLevel": ticket.EscalationLevel,
            "currentAssignedRole": ticket.CurrentAssignedRole,
            "escalationHistory": history,
            "totalEscalations": len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting escalation history for ticket {ticket_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# END ENHANCED ESCALATION API ENDPOINTS
# ============================================================================

# Import Bot Service and SLA Monitor
from bot_service import bot_service
from sla_monitor import sla_monitor

# Initialize services
bot_service.app = app
sla_monitor.app = app

# Start SLA monitoring service only if tables exist
try:
    # Check if migration is complete before starting monitoring
    with app.app_context():
        from sqlalchemy import text
        result = db.session.execute(text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME IN ('sla_logs', 'partners', 'bot_configurations')
        """))
        table_count = result.scalar()
        
        if table_count >= 3:
            sla_monitor.start_monitoring()
            logger.info("SLA monitoring service started successfully")
        else:
            logger.info("SLA monitoring service not started - tables not ready")
except Exception as e:
    logger.warning(f"SLA monitoring service not started: {e}")

# Import extended models
from models import (
    Partner, SLALog, TicketStatusLog, AuditLog, EscalationRule,
    BotConfiguration, BotInteraction
)

# Register Super Admin Blueprint after all models are loaded
register_super_admin_blueprint()

# ================================
# ODOO API ENDPOINTS
# ================================

@app.route('/api/odoo/test-connection', methods=['GET'])
def test_odoo_connection():
    """Test Odoo connection and return status"""
    if not odoo_service:
        return jsonify({
            'status': 'error',
            'message': 'Odoo service not initialized'
        }), 503
    
    try:
        result = odoo_service.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/odoo/customers', methods=['GET', 'POST'])
def odoo_customers():
    """Handle customer operations in Odoo"""
    if not odoo_service:
        return jsonify({'error': 'Odoo service not available'}), 503
    
    if request.method == 'GET':
        try:
            limit = request.args.get('limit', 10, type=int)
            offset = request.args.get('offset', 0, type=int)
            query = request.args.get('q')
            
            if query:
                customers = odoo_service.search_customers(query, limit)
            else:
                customers = odoo_service.get_customers(limit, offset)
            
            return jsonify({
                'status': 'success',
                'customers': customers,
                'count': len(customers)
            })
        except Exception as e:
            logger.error(f"Error getting customers: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'error': 'Customer name is required'}), 400
            
            customer_id = odoo_service.create_customer(
                name=data['name'],
                email=data.get('email'),
                phone=data.get('phone'),
                **{k: v for k, v in data.items() if k not in ['name', 'email', 'phone']}
            )
            
            return jsonify({
                'status': 'success',
                'customer_id': customer_id,
                'message': f'Customer {data["name"]} created successfully'
            }), 201
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/odoo/tickets', methods=['GET', 'POST'])
def odoo_tickets():
    """Handle ticket operations in Odoo"""
    if not odoo_service:
        return jsonify({'error': 'Odoo service not available'}), 503
    
    if request.method == 'GET':
        try:
            limit = request.args.get('limit', 10, type=int)
            offset = request.args.get('offset', 0, type=int)
            partner_id = request.args.get('partner_id', type=int)
            
            if partner_id:
                tickets = odoo_service.get_customer_tickets(partner_id, limit)
            else:
                tickets = odoo_service.get_tickets(limit, offset)
            
            return jsonify({
                'status': 'success',
                'tickets': tickets,
                'count': len(tickets)
            })
        except Exception as e:
            logger.error(f"Error getting tickets: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'error': 'Ticket subject is required'}), 400
            
            ticket_id = odoo_service.create_ticket(
                name=data['name'],
                description=data.get('description', ''),
                partner_id=data.get('partner_id'),
                priority=data.get('priority', '1'),
                **{k: v for k, v in data.items() if k not in ['name', 'description', 'partner_id', 'priority']}
            )
            
            return jsonify({
                'status': 'success',
                'ticket_id': ticket_id,
                'message': f'Ticket "{data["name"]}" created successfully'
            }), 201
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/odoo/tickets/<int:ticket_id>', methods=['PUT'])
def update_odoo_ticket(ticket_id):
    """Update a ticket in Odoo"""
    if not odoo_service:
        return jsonify({'error': 'Odoo service not available'}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        result = odoo_service.update_ticket(ticket_id, **data)
        
        return jsonify({
            'status': 'success',
            'message': f'Ticket {ticket_id} updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")
        return jsonify({'error': str(e)}), 500

###############################################################
# Generic Odoo API Endpoints for All Models and Methods
###############################################################

# Example usage:
# POST /api/odoo/<model>/<method>
# Body: { "args": [...], "kwargs": {...} }

@app.route('/api/odoo/<model>/<method>', methods=['POST'])
def odoo_generic_api(model, method):
    """Generic endpoint to call any Odoo model method"""
    if not odoo_service:
        return jsonify({'error': 'Odoo service not available'}), 503
    data = request.get_json() or {}
    args = data.get('args', [])
    kwargs = data.get('kwargs', {})
    try:
        result = odoo_service.models.execute_kw(
            odoo_service.db, odoo_service.uid, odoo_service.password,
            model, method, args, kwargs
        )
        return jsonify({'result': result})
    except Exception as e:
        logger.error(f"Odoo API error: {e}")
        return jsonify({'error': str(e)}), 500

# Example: GET metadata for a model
@app.route('/api/odoo/<model>/fields_get', methods=['GET'])
def odoo_model_fields_get(model):
    if not odoo_service:
        return jsonify({'error': 'Odoo service not available'}), 503
    try:
        result = odoo_service.models.execute_kw(
            odoo_service.db, odoo_service.uid, odoo_service.password,
            model, 'fields_get', [], {'attributes': ['string', 'help', 'type']}
        )
        return jsonify({'fields': result})
    except Exception as e:
        logger.error(f"Odoo fields_get error: {e}")
        return jsonify({'error': str(e)}), 500

try:
    from uv_integration import generate_uv_token, validate_uv_api_key, uv_auth_required, add_uv_response_metadata, apply_query_filters
    
    @app.route('/api/generate-uv-token', methods=['POST'])
    def generate_uv_access_token():
        """Generate access token for Urban Vyapari integration"""
        try:
            data = request.json
            if not data:
                return jsonify({'success': False, 'error': 'JSON data required'}), 400
            
            # Validate Urban Vyapari API key
            uv_api_key = data.get('uv_api_key')
            if not validate_uv_api_key(uv_api_key):
                return jsonify({'success': False, 'error': 'Invalid Urban Vyapari API key'}), 401
            
            # Extract admin information
            admin_info = {
                'admin_id': data.get('admin_id'),
                'admin_name': data.get('admin_name'),
                'admin_email': data.get('admin_email')
            }
            
            # Validate required fields
            if not all(admin_info.values()):
                return jsonify({'success': False, 'error': 'admin_id, admin_name, and admin_email are required'}), 400
            
            # Generate token
            token = generate_uv_token(admin_info)
            
            logger.info(f"Generated Urban Vyapari token for admin: {admin_info['admin_name']} ({admin_info['admin_email']})")
            
            return jsonify({
                'success': True,
                'access_token': token,
                'token_type': 'Bearer',
                'expires_in': 86400,  # 24 hours in seconds
                'admin_info': admin_info
            })
            
        except Exception as e:
            logger.error(f"Error generating Urban Vyapari token: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/tickets-portal')
    def tickets_portal_uv():
        """Web portal for Urban Vyapari tickets integration"""
        try:
            from uv_integration import validate_uv_token
            
            token = request.args.get('token')
            
            if not token:
                return render_template('uv_token_required.html'), 401
            
            # Validate token
            payload = validate_uv_token(token)
            if not payload:
                return render_template('uv_invalid_token.html'), 401
            
            # Get initial filters from query params
            filters = apply_query_filters(request.args)
            
            logger.info(f"Urban Vyapari admin accessing tickets portal: {payload['admin_name']}")
            
            return render_template('uv_tickets_portal.html', 
                                 token=token, 
                                 admin=payload,
                                 filters=filters)
                                 
        except Exception as e:
            logger.error(f"Error in tickets portal: {str(e)}")
            return render_template('uv_error.html', error=str(e)), 500
    
    logger.info("Urban Vyapari integration endpoints loaded successfully")
    
except ImportError as e:
    logger.warning(f"Urban Vyapari integration not available: {e}")

if __name__ == '__main__':
    logger.info("Starting YouCloudTech Chatbot Application...")
    try:
        db.create_all()
        logger.info("Database tables created successfully")
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"Error starting application: {e}")
