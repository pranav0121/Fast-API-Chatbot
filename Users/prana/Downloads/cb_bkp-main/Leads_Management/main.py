from flask import Flask, jsonify, request
from flask_cors import CORS
import uuid
import json
from datetime import datetime
from config import Config
from services import QuestionService, AnswerService, ScoringService, LeadService
from database import Base, engine

# Import new services
from notification_service import NotificationService
from ab_testing_service import ABTestingService

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # Enable CORS for frontend integration

# Database session teardown


@app.teardown_appcontext
def close_db(error):
    """Close database session after each request."""
    from database import close_db_session
    close_db_session()


# Create all tables
Base.metadata.create_all(engine)


@app.route('/')
def home():
    """Serve the lead capture form."""
    # ...existing code...
    # Removed static file serving for backend-only implementation
    return jsonify({'message': 'Endpoint not available in backend-only version'}), 404


@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start a new lead capture session."""
    data = request.json or {}
    session_id = str(uuid.uuid4())
    utm_source = data.get('utm_source', 'direct')

    success = LeadService.create_lead(session_id, utm_source)
    if success:
        return jsonify({
            'session_id': session_id,
            'message': 'Session started successfully'
        }), 200
    return jsonify({'message': 'Failed to start session'}), 400


@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Fetch predefined questions."""
    questions = QuestionService.get_questions()
    return jsonify(questions)


@app.route('/api/answer', methods=['POST'])
def log_answer():
    """Log a single answer and return updated score."""
    data = request.json
    session_id = data.get('session_id')
    question_id = data.get('question_id')
    answer_text = data.get('answer_text')
    time_taken = data.get('time_taken')

    if not all([session_id, question_id, answer_text]):
        return jsonify({'message': 'Missing required fields'}), 400

    success, score = AnswerService.log_answer(
        session_id, question_id, answer_text, time_taken)
    if success:
        return jsonify({
            'message': 'Answer logged successfully',
            'score_earned': score
        }), 200
    return jsonify({'message': 'Failed to log answer'}), 400


@app.route('/api/behavior', methods=['POST'])
def log_behavior():
    """Log user behavior and return score change."""
    data = request.json
    session_id = data.get('session_id')
    action = data.get('action')
    metadata = data.get('metadata')

    if not all([session_id, action]):
        app.logger.error(
            f"Missing required fields: session_id={session_id}, action={action}")
        return jsonify({'message': 'Missing required fields'}), 400

    score_change = ScoringService.log_behavior(session_id, action, metadata)
    app.logger.info(
        f"Behavior logged: session_id={session_id}, action={action}, metadata={metadata}, score_change={score_change}")
    return jsonify({
        'message': 'Behavior logged successfully',
        'score_change': score_change
    }), 200


@app.route('/api/lead/profile', methods=['POST'])
def update_lead_profile():
    """Update lead profile information."""
    data = request.json
    session_id = data.get('session_id')
    profile_data = data.get('profile_data', {})

    if not session_id:
        return jsonify({'message': 'Missing session_id'}), 400

    success = LeadService.update_lead_profile(session_id, profile_data)
    if success:
        return jsonify({'message': 'Profile updated successfully'}), 200
    return jsonify({'message': 'Failed to update profile'}), 400


@app.route('/api/lead/summary/<session_id>', methods=['GET'])
def get_lead_summary(session_id):
    """Get complete lead summary for CRM export."""
    summary = LeadService.get_lead_summary(session_id)
    if summary:
        return jsonify(summary), 200
    return jsonify({'message': 'Lead not found'}), 404


@app.route('/api/score/<session_id>', methods=['GET'])
def get_current_score(session_id):
    """Get current lead score and type."""
    summary = LeadService.get_lead_summary(session_id)
    if summary:
        return jsonify({
            'lead_score': summary['lead_score'],
            'lead_type': summary['lead_type']
        }), 200
    return jsonify({'message': 'Lead not found'}), 404


@app.route('/api/product-menu', methods=['GET'])
def get_product_menu():
    """Get product discovery menu options."""
    from workflow_config import WORKFLOW_CONFIG
    return jsonify(WORKFLOW_CONFIG['product_menu'])


@app.route('/api/cta-options', methods=['GET'])
def get_cta_options():
    """Get final call-to-action options."""
    from workflow_config import WORKFLOW_CONFIG
    return jsonify(WORKFLOW_CONFIG['cta_options'])


@app.route('/api/lead/export/<session_id>', methods=['GET'])
def export_lead_data(session_id):
    """Export lead data in CRM format."""
    summary = LeadService.get_lead_summary(session_id)
    if summary:
        # Format for CRM export
        crm_data = {
            "name": summary.get('name', 'Unknown'),
            "location": summary.get('location', ''),
            "business_type": summary.get('business_type', ''),
            "staff_size": summary.get('staff_size', ''),
            "monthly_sales": summary.get('monthly_sales', ''),
            "features_interested": summary.get('features_interested', []),
            "contact_info": summary.get('phone', summary.get('email', '')),
            "email": summary.get('email', ''),
            "phone": summary.get('phone', ''),
            "lead_score": summary.get('lead_score', 0),
            "lead_type": summary.get('lead_type', 'Unqualified'),
            "utm_source": summary.get('utm_source', 'direct'),
            "session_start_time": summary.get('created_at', ''),
            "assigned_to": "CTL-Team"  # Default assignment
        }
        return jsonify(crm_data), 200
    return jsonify({'message': 'Lead not found'}), 404


@app.route('/api/analytics/leads', methods=['GET'])
def get_leads_analytics():
    """Get leads analytics data."""
    try:
        # This would typically query the database for analytics
        # For now, returning sample data structure
        analytics = {
            "total_leads": 0,
            "sql_leads": 0,
            "mql_leads": 0,
            "unqualified_leads": 0,
            "conversion_rate": 0,
            "average_score": 0,
            "completion_rate": 0
        }
        return jsonify(analytics), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/leads/list', methods=['GET'])
def get_leads_list():
    """Get list of all leads for sales team review."""
    try:
        from database import get_db_session, close_db_session
        from models import Lead

        db_session = get_db_session()
        try:
            leads = db_session.query(Lead).order_by(
                Lead.created_at.desc()).all()

            leads_data = []
            for lead in leads:
                try:
                    # Safely parse features_interested JSON
                    features = []
                    if lead.features_interested:
                        try:
                            if isinstance(lead.features_interested, str):
                                features = json.loads(lead.features_interested)
                            elif isinstance(lead.features_interested, list):
                                features = lead.features_interested
                            else:
                                features = [str(lead.features_interested)]
                        except (json.JSONDecodeError, TypeError):
                            features = [str(lead.features_interested)]

                    lead_data = {
                        'session_id': lead.session_id,
                        'name': lead.name or 'Anonymous',
                        'email': lead.email,
                        'phone': lead.phone,
                        'business_type': lead.business_type,
                        'location': lead.location,
                        'staff_size': lead.staff_size,
                        'monthly_sales': lead.monthly_sales,
                        'features_interested': features,
                        'lead_score': lead.lead_score,
                        'lead_type': lead.lead_type,
                        'utm_source': lead.utm_source,
                        'created_at': lead.created_at.isoformat() if lead.created_at else None,
                        'updated_at': lead.updated_at.isoformat() if lead.updated_at else None
                    }
                    leads_data.append(lead_data)
                except Exception as lead_error:
                    print(
                        f"Error processing lead {lead.id}: {str(lead_error)}")
                    continue

            return jsonify({
                'leads': leads_data,
                'total_count': len(leads_data)
            }), 200

        finally:
            db_session.close()
            close_db_session()

    except Exception as e:
        print(f"Database error in get_leads_list: {str(e)}")
        return jsonify({
            'error': f'Database error: {str(e)}',
            'leads': [],
            'total_count': 0
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/leads/dashboard')
def leads_dashboard():
    """Serve a simple dashboard for viewing leads."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leads Dashboard</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container mt-4">
            <h1>Leads Dashboard</h1>
            <div id="leadsTable"></div>
        </div>
        <script>
            fetch('/api/leads/list')
                .then(response => response.json())
                .then(data => {
                    const table = document.createElement('table');
                    table.className = 'table table-striped';
                    table.innerHTML = `
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Contact</th>
                                <th>Business Type</th>
                                <th>Location</th>
                                <th>Score</th>
                                <th>Lead Type</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.leads.map(lead => `
                                <tr>
                                    <td>${lead.name || 'Anonymous'}</td>
                                    <td>${lead.email || lead.phone || 'N/A'}</td>
                                    <td>${lead.business_type || 'N/A'}</td>
                                    <td>${lead.location || 'N/A'}</td>
                                    <td><span class="badge bg-primary">${lead.lead_score}</span></td>
                                    <td><span class="badge ${lead.lead_type === 'SQL' ? 'bg-success' : lead.lead_type === 'MQL' ? 'bg-warning' : 'bg-secondary'}">${lead.lead_type || 'Unqualified'}</span></td>
                                    <td>${lead.created_at ? new Date(lead.created_at).toLocaleDateString() : 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    `;
                    document.getElementById('leadsTable').appendChild(table);
                })
                .catch(error => console.error('Error:', error));
        </script>
    </body>
    </html>
    '''


@app.route('/chatbot')
def chatbot_page():
    """Serve the original chatbot HTML page."""
    return app.send_static_file('chatbot.html')


@app.route('/dashboard')
def advanced_dashboard():
    """Serve the advanced analytics dashboard."""
    return app.send_static_file('advanced_dashboard.html')


# =================== NEW ENHANCED API ENDPOINTS ===================

@app.route('/api/ab-test/variant/<test_name>', methods=['POST'])
def get_ab_test_variant(test_name):
    """Get A/B test variant for user session"""
    try:
        data = request.json or {}
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400

        variant_config = ABTestingService.get_variant_config(
            session_id, test_name)
        return jsonify(variant_config), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ab-test/conversion', methods=['POST'])
def log_ab_test_conversion():
    """Log A/B test conversion event"""
    try:
        data = request.json
        session_id = data.get('session_id')
        test_name = data.get('test_name')
        variant = data.get('variant')
        conversion_type = data.get('conversion_type')
        conversion_value = data.get('conversion_value')

        if not all([session_id, test_name, variant, conversion_type]):
            return jsonify({'error': 'Missing required fields'}), 400

        ABTestingService.log_conversion(
            session_id, test_name, variant, conversion_type, conversion_value)

        return jsonify({'message': 'Conversion logged successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ab-test/results', methods=['GET'])
def get_ab_test_results():
    """Get A/B test performance results"""
    try:
        test_name = request.args.get('test_name')
        results = ABTestingService.get_test_results(test_name)

        return jsonify({
            'results': results,
            'generated_at': datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/send', methods=['POST'])
def send_lead_notification():
    """Manually trigger lead notification"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400

        # Get lead data
        lead_summary = LeadService.get_lead_summary(session_id)
        if not lead_summary:
            return jsonify({'error': 'Lead not found'}), 404

        # Send notifications
        success = NotificationService.notify_sales_team(lead_summary)

        return jsonify({
            'message': 'Notification sent' if success else 'Notification failed',
            'success': success
        }), 200 if success else 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/enhanced', methods=['GET'])
def get_enhanced_analytics():
    """Get enhanced analytics with A/B testing and real-time data"""
    try:
        from database import get_db_session
        from models import Lead, Answer, UserBehavior
        from datetime import datetime, timedelta

        db_session = get_db_session()

        # Get date range
        days = int(request.args.get('days', 7))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Basic metrics
        leads = db_session.query(Lead).filter(
            Lead.created_at >= start_date
        ).all()

        total_leads = len(leads)
        sql_leads = len([l for l in leads if l.lead_type == 'SQL'])
        mql_leads = len([l for l in leads if l.lead_type == 'MQL'])
        unqualified = len([l for l in leads if l.lead_type == 'Unqualified'])

        # Conversion funnel
        total_sessions = total_leads
        engaged_users = len([l for l in leads if l.lead_score > 20])
        qualified_users = sql_leads + mql_leads

        # Response time analysis
        response_times = []
        behaviors = db_session.query(UserBehavior).filter(
            UserBehavior.created_at >= start_date,
            UserBehavior.action.like('%response%')
        ).all()

        for behavior in behaviors:
            try:
                data = json.loads(behavior.behavior_metadata)
                if 'response_time' in data:
                    response_times.append(data['response_time'])
            except:
                continue

        avg_response_time = sum(response_times) / \
            len(response_times) if response_times else 0

        # A/B test performance
        ab_results = ABTestingService.get_test_results()

        # Channel performance
        channel_data = {}
        for lead in leads:
            source = lead.utm_source or 'direct'
            if source not in channel_data:
                channel_data[source] = {'total': 0, 'sql': 0}
            channel_data[source]['total'] += 1
            if lead.lead_type == 'SQL':
                channel_data[source]['sql'] += 1

        # Real-time leads (last 24 hours)
        recent_leads = db_session.query(Lead).filter(
            Lead.created_at >= datetime.now() - timedelta(hours=24),
            Lead.lead_score >= 100
        ).order_by(Lead.created_at.desc()).limit(10).all()

        realtime_leads = []
        for lead in recent_leads:
            realtime_leads.append({
                'session_id': lead.session_id,
                'name': lead.name or 'Anonymous',
                'business_type': lead.business_type,
                'lead_score': lead.lead_score,
                'lead_type': lead.lead_type,
                'created_at': lead.created_at.isoformat() if lead.created_at else None
            })

        db_session.close()

        return jsonify({
            'conversion_metrics': {
                'total_leads': total_leads,
                'sql_leads': sql_leads,
                'mql_leads': mql_leads,
                'unqualified_leads': unqualified,
                'sql_conversion_rate': (sql_leads / total_leads * 100) if total_leads > 0 else 0,
                'mql_conversion_rate': (mql_leads / total_leads * 100) if total_leads > 0 else 0,
                'average_score': sum([l.lead_score for l in leads]) / total_leads if total_leads > 0 else 0
            },
            'funnel_data': {
                'visitors': total_sessions * 2,  # Approximate
                'engaged': engaged_users,
                'qualified': qualified_users,
                'sql': sql_leads,
                'converted': int(sql_leads * 0.3)  # Approximate conversion
            },
            'response_time': {
                'average': avg_response_time,
                'data_points': len(response_times)
            },
            'channel_performance': channel_data,
            'ab_test_results': ab_results,
            'realtime_leads': realtime_leads,
            'generated_at': datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lead/notify', methods=['POST'])
def auto_notify_lead():
    """Automatically check and notify for high-value leads"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400

        # Get current lead data
        lead_summary = LeadService.get_lead_summary(session_id)
        if not lead_summary:
            return jsonify({'error': 'Lead not found'}), 404

        # Check if notification should be sent
        lead_score = lead_summary.get('lead_score', 0)
        lead_type = lead_summary.get('lead_type', 'Unqualified')

        notification_sent = False
        if lead_type == 'SQL' and lead_score >= 60:
            notification_sent = NotificationService.notify_sales_team(
                lead_summary)

        return jsonify({
            'notification_sent': notification_sent,
            'lead_score': lead_score,
            'lead_type': lead_type,
            'qualifies_for_notification': lead_type == 'SQL' and lead_score >= 60
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
