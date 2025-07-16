from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

# Device Tracking Import
from device_tracker_core import DeviceInfo

# Define auth blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Import here to avoid circular imports
    from app import db, User
    from datetime import datetime
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(Email=email).first()
        
        if not user:
            flash('Email not found. Please check your email or register first.', 'error')
            return redirect(url_for('auth.login'))
        
        if not check_password_hash(user.PasswordHash, password):
            flash('Invalid password. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.IsActive:
            flash('Your account has been deactivated. Please contact support.', 'error')
            return redirect(url_for('auth.login'))
        
        # Update last login time
        user.LastLogin = datetime.utcnow()
        
        # 🔥 NEW: Capture device tracking information for login
        try:
            # Extract device info from Flask request
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Create DeviceInfo instance
            device_info = DeviceInfo(user_agent_string=user_agent, ip_address=ip_address)
            device_data = device_info.get_complete_info()
            
            if device_data:
                browser_info = device_data.get('browser', {})
                os_info = device_data.get('os', {})
                
                user.device_type = device_data.get('device_type')
                user.operating_system = os_info.get('family') if os_info else None
                user.browser = browser_info.get('family') if browser_info else None
                user.browser_version = browser_info.get('version_string') if browser_info else None
                user.os_version = os_info.get('version_string') if os_info else None
                user.device_brand = None  # Not available in simple parser
                user.device_model = None  # Not available in simple parser
                user.device_fingerprint = f"{device_data.get('device_type')}_{browser_info.get('family', 'unknown')}_{os_info.get('family', 'unknown')}" if browser_info and os_info else None
                user.user_agent = device_data.get('user_agent')
                user.ip_address = device_data.get('ip_address')
        except Exception as e:
            print(f"Warning: Could not capture device info for user {user.Email}: {e}")
        
        try:
            db.session.commit()
        except:
            db.session.rollback()
        
        login_user(user)
        flash(f'Welcome back, {user.Name}!', 'success')
        return redirect(url_for('index'))
    
    try:
        return render_template('login_simple.html')
    except Exception as e:
        return f"Error rendering login template: {str(e)}"

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Import here to avoid circular imports
    from app import db, User
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        organization = request.form.get('organization')
        position = request.form.get('position')
        department = request.form.get('department')
        phone = request.form.get('phone')
        priority = request.form.get('priority')
        
        # Validate required fields
        if not all([name, email, password, organization, priority]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('auth.register'))
        
        # Validate priority level
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if priority not in valid_priorities:
            flash('Invalid priority level selected', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        user = User.query.filter_by(Email=email).first()
        if user:
            flash('Email address already registered', 'warning')
            return redirect(url_for('auth.register'))
        
        # Create new user with organization and priority information
        new_user = User(
            Name=name,
            Email=email,
            PasswordHash=generate_password_hash(password),
            OrganizationName=organization,
            Position=position,
            Department=department,
            Phone=phone,
            PriorityLevel=priority
        )
        
        # 🔥 NEW: Capture device tracking information for registration
        try:
            # Extract device info from Flask request
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Create DeviceInfo instance
            device_info = DeviceInfo(user_agent_string=user_agent, ip_address=ip_address)
            device_data = device_info.get_complete_info()
            
            if device_data:
                browser_info = device_data.get('browser', {})
                os_info = device_data.get('os', {})
                
                new_user.device_type = device_data.get('device_type')
                new_user.operating_system = os_info.get('family') if os_info else None
                new_user.browser = browser_info.get('family') if browser_info else None
                new_user.browser_version = browser_info.get('version_string') if browser_info else None
                new_user.os_version = os_info.get('version_string') if os_info else None
                new_user.device_brand = None  # Not available in simple parser
                new_user.device_model = None  # Not available in simple parser
                new_user.device_fingerprint = f"{device_data.get('device_type')}_{browser_info.get('family', 'unknown')}_{os_info.get('family', 'unknown')}" if browser_info and os_info else None
                new_user.user_agent = device_data.get('user_agent')
                new_user.ip_address = device_data.get('ip_address')
        except Exception as e:
            print(f"Warning: Could not capture device info for new user {email}: {e}")
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in with your credentials.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Admin Authentication Routes
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login route with credential validation and auto-creation"""
    # Import here to avoid circular imports
    from app import db, User
    from datetime import datetime
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Debug: Check if this is the expected admin email
        if email == 'admin@youcloudtech.com':
            # Auto-create admin user if it doesn't exist
            admin_user = User.query.filter_by(Email=email).first()
            
            if not admin_user:
                # Create admin user automatically
                try:
                    admin_user = User(
                        Name='System Administrator',
                        Email=email,
                        PasswordHash=generate_password_hash('admin123'),
                        OrganizationName='YouCloudTech',
                        Position='Administrator',
                        PriorityLevel='critical',
                        Department='IT',
                        Phone='+1-555-ADMIN',
                        IsActive=True,
                        IsAdmin=True,
                        CreatedAt=datetime.utcnow(),
                        LastLogin=datetime.utcnow()
                    )
                    db.session.add(admin_user)
                    db.session.commit()
                    flash('Admin user created automatically. Please login.', 'success')
                    return redirect(url_for('auth.admin_login'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error creating admin user: {str(e)}', 'error')
                    return redirect(url_for('auth.admin_login'))
            
            # Ensure existing user is properly configured as admin
            if not admin_user.IsAdmin or not admin_user.IsActive:
                try:
                    admin_user.IsAdmin = True
                    admin_user.IsActive = True
                    admin_user.PasswordHash = generate_password_hash('admin123')
                    db.session.commit()
                    flash('Admin user activated automatically.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error updating admin user: {str(e)}', 'error')
        
        # Validate admin credentials
        admin_user = User.query.filter_by(Email=email, IsAdmin=True).first()
        
        if not admin_user:
            flash('Invalid admin credentials. Access denied.', 'error')
            return redirect(url_for('auth.admin_login'))
        
        if not check_password_hash(admin_user.PasswordHash, password):
            flash('Invalid admin password. Access denied.', 'error')
            return redirect(url_for('auth.admin_login'))
        
        if not admin_user.IsActive:
            flash('Admin account has been deactivated. Contact system administrator.', 'error')
            return redirect(url_for('auth.admin_login'))
        
        # Update last login time
        admin_user.LastLogin = datetime.utcnow()
        try:
            db.session.commit()
        except:
            db.session.rollback()
        
        # Create admin session
        from flask import session
        session['admin_logged_in'] = True
        session['admin_user_id'] = admin_user.UserID
        session['admin_email'] = admin_user.Email
        session['admin_name'] = admin_user.Name
        
        flash(f'Welcome, Administrator {admin_user.Name}!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_login.html')

@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login_alt():
    """Admin login route with auto-creation for admin@youcloudtech.com"""
    from app import db, User
    from datetime import datetime
    from flask import session
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check for admin email
        if email == 'admin@youcloudtech.com':
            user = User.query.filter_by(Email=email).first()
            
            # Auto-create admin user if doesn't exist
            if not user:
                admin_user = User(
                    Name='System Administrator',
                    Email='admin@youcloudtech.com',
                    PasswordHash=generate_password_hash('SecureAdmin123!'),
                    Organization='YouCloud Technologies',
                    Position='System Administrator',
                    Department='IT',
                    Phone='Admin',
                    Priority='critical',
                    IsActive=True,
                    JoinedAt=datetime.utcnow()
                )
                db.session.add(admin_user)
                db.session.commit()
                user = admin_user
                current_app.logger.info("Admin user auto-created successfully")
            
            # Auto-activate if deactivated
            if not user.IsActive:
                user.IsActive = True
                db.session.commit()
                current_app.logger.info("Admin user auto-activated")
            
            # Verify password
            if check_password_hash(user.PasswordHash, password):
                # Set admin session
                session['admin_logged_in'] = True
                session['admin_user_id'] = user.UserID
                session['admin_email'] = user.Email
                session['admin_name'] = user.Name
                
                flash('Admin login successful!', 'success')
                return redirect(url_for('super_admin.dashboard'))
            else:
                flash('Invalid admin password', 'error')
        else:
            flash('Admin access restricted to authorized accounts only', 'error')
    
    return render_template('admin_login.html')

@auth_bp.route('/admin/logout')
def admin_logout():
    """Admin logout route"""
    from flask import session
    
    # Clear admin session
    session.pop('admin_logged_in', None)
    session.pop('admin_user_id', None)
    session.pop('admin_email', None)
    session.pop('admin_name', None)
    
    flash('Admin logged out successfully.', 'success')
    return redirect(url_for('auth.admin_login'))

def admin_required(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    from flask import session, redirect, url_for, flash
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin authentication required.', 'error')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function
