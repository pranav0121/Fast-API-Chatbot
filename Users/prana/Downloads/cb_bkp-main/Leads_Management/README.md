# Leads-Management

=======

# Lead Capture Bot - Backend Implementation

## Overview

This is a comprehensive lead capture and scoring system implemented as a web-based chatbot backend. The system captures leads through an interactive questionnaire, scores them based on behavior and responses, and qualifies them as SQL, MQL, or Unqualified leads.

## Features Implemented

### ✅ Complete Workflow Implementation

1. **Session Management**: Unique session tracking for each user
2. **Dynamic Question Flow**: Progressive questionnaire based on workflow requirements
3. **Behavior Scoring**: Real-time scoring based on user interactions
4. **Lead Qualification**: Automatic classification as SQL/MQL/Unqualified
5. **Profile Data Collection**: Comprehensive user profile building
6. **CRM Export Ready**: Structured data format for CRM integration

# Lead Capture Bot – Backend Only

> **Note:** This repository contains only the backend logic. Frontend UI and database provisioning (PostgreSQL) will be handled by other teams.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Scoring System](#scoring-system)
- [Setup & Installation](#setup--installation)
- [Environment Configuration](#environment-configuration)
- [Database Models](#database-models)
- [Business Logic](#business-logic)
- [A/B Testing](#ab-testing)
- [Notifications](#notifications)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## 🎯 Overview

This is a **backend-only** implementation of an intelligent lead capture and scoring system. It provides RESTful APIs for chatbot integration, lead management, behavioral scoring, and classification. The system is designed to:

- Capture leads through conversational interfaces
- Score user behavior in real-time
- Classify leads as SQL (Sales Qualified Lead), MQL (Marketing Qualified Lead), or Unqualified
- Support A/B testing for optimization
- Send notifications for high-value leads
- Export lead data in CRM-ready formats

---

## ✨ Features

### 🚀 Core Functionality

- **Session Management**: Unique session tracking for each user interaction
- **Dynamic Question Flow**: Progressive questionnaire based on workflow configuration
- **Real-time Scoring**: Behavioral scoring engine with configurable rules
- **Lead Classification**: Automatic categorization (SQL/MQL/Unqualified)
- **Profile Collection**: Comprehensive lead data capture
- **CRM Integration**: Export-ready lead data with scoring

### 🧠 Advanced Features

- **A/B Testing Framework**: Built-in experimentation platform
- **Notification System**: Multi-channel alerts (Email, Slack, Discord, Teams)
- **Analytics Engine**: Conversion tracking and performance metrics
- **Workflow Configuration**: Flexible question and scoring rules
- **Database Abstraction**: PostgreSQL with SQLAlchemy ORM

---

## 📁 Project Structure

```
lead-capture-backend/
├── 📄 README.md                    # This documentation
├── ⚙️ .env                        # Environment configuration
├── 📦 requirements.txt             # Python dependencies
├── 🗂️ archive/                    # Archived frontend files
│   ├── static/                     # Previous frontend assets
│   └── README.txt                  # Archive information
├── 🌐 main.py                     # Flask application & API routes
├── 🗄️ database.py                 # Database connection & session management
├── 📊 models.py                   # SQLAlchemy database models
├── 🔧 services.py                 # Business logic & services
├── ⚙️ config.py                   # Application configuration
├── 📋 workflow_config.py          # Question flow & scoring rules
├── 📧 notification_service.py     # Multi-channel notifications
├── 🧪 ab_testing_service.py       # A/B testing framework
├── 🔍 check_database.py           # Database utilities & debugging
└── 📝 schemas.py                  # Data validation schemas
```

### 📄 File Descriptions

| File                      | Purpose                     | Key Functions                                   |
| ------------------------- | --------------------------- | ----------------------------------------------- |
| `main.py`                 | API endpoints and Flask app | Session management, question flow, lead capture |
| `models.py`               | Database schema definitions | Lead, Answer, UserBehavior models               |
| `services.py`             | Business logic layer        | QuestionService, ScoringService, LeadService    |
| `database.py`             | Database connectivity       | PostgreSQL connection, session management       |
| `config.py`               | Environment configuration   | Database URLs, API keys, feature flags          |
| `workflow_config.py`      | Workflow definitions        | Questions, scoring rules, thresholds            |
| `notification_service.py` | Alert system                | Email, Slack, Discord notifications             |
| `ab_testing_service.py`   | Experimentation             | A/B test management and analytics               |

---

## 🛠 API Endpoints

### Core Workflow APIs

| Method   | Endpoint             | Purpose                  | Request Body                                                              |
| -------- | -------------------- | ------------------------ | ------------------------------------------------------------------------- |
| **POST** | `/api/session/start` | Start a new lead session | `{"utm_source": "string"}`                                                |
| **GET**  | `/api/questions`     | Fetch question flow      | -                                                                         |
| **POST** | `/api/answer`        | Log user answer          | `{"session_id": "string", "question_id": "int", "answer_text": "string"}` |
| **POST** | `/api/behavior`      | Track user behavior      | `{"session_id": "string", "action": "string", "metadata": "object"}`      |
| **POST** | `/api/lead/profile`  | Update lead profile      | `{"session_id": "string", "profile_data": "object"}`                      |

### Data Retrieval APIs

| Method  | Endpoint                         | Purpose                            | Response                                |
| ------- | -------------------------------- | ---------------------------------- | --------------------------------------- |
| **GET** | `/api/lead/summary/<session_id>` | Get complete lead summary          | Lead data with score and classification |
| **GET** | `/api/lead/export/<session_id>`  | Export in CRM format               | Structured lead data                    |
| **GET** | `/api/score/<session_id>`        | Get current score & classification | Score breakdown and category            |

### Support APIs

| Method  | Endpoint               | Purpose                      |
| ------- | ---------------------- | ---------------------------- |
| **GET** | `/api/product-menu`    | Get product/service options  |
| **GET** | `/api/cta-options`     | Get call-to-action options   |
| **GET** | `/api/analytics/leads` | Get analytics dashboard data |

### A/B Testing APIs

| Method   | Endpoint                           | Purpose              |
| -------- | ---------------------------------- | -------------------- |
| **POST** | `/api/ab-test/variant/<test_name>` | Get A/B test variant |
| **POST** | `/api/ab-test/conversion`          | Log conversion event |

---

## 🎯 Scoring System

### Behavioral Scoring Rules

| Action                          | Score | Description                   |
| ------------------------------- | ----- | ----------------------------- |
| **Session opened**              | +5    | User starts interaction       |
| **Replied to greeting**         | +5    | User engages with bot         |
| **Each question answered**      | +5    | Progressive engagement        |
| **All questions completed**     | +10   | Full questionnaire completion |
| **Contact shared**              | +10   | Provides contact information  |
| **Product interest**            | +5    | Shows interest in features    |
| **Demo requested**              | +15   | High-intent action            |
| **Quick reply (<2 min)**        | +5    | Fast engagement               |
| **Detailed answer (>10 chars)** | +5    | Quality responses             |
| **CTA clicked**                 | +15   | Conversion action             |

### Lead Classification

```python
def classify_lead(score):
    if score >= 60:
        return "SQL"  # Sales Qualified Lead
    elif score >= 30:
        return "MQL"  # Marketing Qualified Lead
    else:
        return "Unqualified"
```

### Score Calculation Example

```python
# Example user journey:
session_opened = 5
answered_questions = 25  # 5 questions × 5 points
completed_all = 10
shared_contact = 10
clicked_demo = 15
quick_replies = 15  # 3 quick replies × 5 points

total_score = 80  # → SQL Lead
```

---

## ⚙️ Setup & Installation

### Prerequisites

- **Python 3.8+**
- **PostgreSQL 12+**
- **Git**

### 1. Clone Repository

```bash
git clone <repository-url>
cd lead-capture-backend
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE lead_management;
CREATE USER lead_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE lead_management TO lead_user;
```

### 5. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your database credentials
```

### 6. Run Database Migrations

```bash
# If using Alembic (recommended)
alembic upgrade head

# Or create tables directly
python -c "from database import Base, engine; Base.metadata.create_all(engine)"
```

### 7. Start the Application

```bash
python main.py
```

The API will be available at `http://localhost:5000`

---

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/lead_management

# Application Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Email Notifications
SENDER_EMAIL=leads@yourdomain.com
SENDER_PASSWORD=app-specific-password
SALES_TEAM_EMAILS=sales@yourdomain.com,manager@yourdomain.com

# Webhook Integrations
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK
TEAMS_WEBHOOK_URL=https://yourdomain.webhook.office.com/webhookb2/YOUR/WEBHOOK

# Feature Flags
AB_TESTING_ENABLED=True
ANALYTICS_RETENTION_DAYS=90
REALTIME_UPDATES_INTERVAL=30
```

### Optional Configuration

```bash
# CORS Settings (if needed for frontend)
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

---

## 🗄️ Database Models

### Lead Model

```python
class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    business_type = Column(String(255))
    location = Column(String(255))
    staff_size = Column(String(100))
    monthly_sales = Column(String(100))
    features_interested = Column(Text)  # JSON string
    lead_score = Column(Integer, default=0)
    lead_classification = Column(String(50))
    utm_source = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Answer Model

```python
class Answer(Base):
    __tablename__ = 'answers'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)
    question_id = Column(Integer, nullable=False)
    question_text = Column(Text)
    answer_text = Column(Text, nullable=False)
    time_taken = Column(Integer)  # seconds
    created_at = Column(DateTime, default=datetime.utcnow)
```

### UserBehavior Model

```python
class UserBehavior(Base):
    __tablename__ = 'user_behaviors'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)
    behavior_type = Column(String(100), nullable=False)
    behavior_metadata = Column(Text)  # JSON string
    score_impact = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

---

## 🔧 Business Logic

### Service Classes

#### QuestionService

```python
class QuestionService:
    @staticmethod
    def get_questions():
        """Return workflow questions from config"""

    @staticmethod
    def get_question_by_id(question_id):
        """Get specific question details"""
```

#### ScoringService

```python
class ScoringService:
    @staticmethod
    def calculate_score(session_id):
        """Calculate total score for session"""

    @staticmethod
    def classify_lead(score):
        """Classify lead based on score thresholds"""

    @staticmethod
    def log_behavior(session_id, behavior, metadata=None):
        """Log user behavior and update score"""
```

#### LeadService

```python
class LeadService:
    @staticmethod
    def create_lead(session_id, utm_source=None):
        """Create new lead record"""

    @staticmethod
    def update_profile(session_id, profile_data):
        """Update lead profile information"""

    @staticmethod
    def get_lead_summary(session_id):
        """Get complete lead data with score"""
```

### Workflow Configuration

```python
# workflow_config.py
WORKFLOW_CONFIG = {
    "scoring": {
        "session_opened": 5,
        "replied_to_greeting": 5,
        "answered_question": 5,
        "answered_all_questions": 10,
        "shared_contact": 10,
        "clicked_product": 5,
        "clicked_demo": 15,
        "cta_clicked": 15
    },
    "classification_thresholds": {
        "sql_threshold": 60,
        "mql_threshold": 30
    },
    "questions": [
        {
            "id": 1,
            "text": "What type of business do you run?",
            "options": ["Restaurant", "Retail Store", "Service Business", "E-commerce", "Other"],
            "step": "profile"
        }
        # ... more questions
    ]
}
```

---

## 🧪 A/B Testing

### A/B Test Configuration

```python
# A/B test variants
ACTIVE_TESTS = {
    'greeting_message': {
        'A': {"text": "Hi! Welcome to YouShop!"},
        'B': {"text": "🔥 Transform your business with YouShop!"}
    },
    'question_flow': {
        'A': {"order": ["business_type", "location", "staff_size"]},
        'B': {"order": ["staff_size", "business_type", "location"]}
    }
}
```

### A/B Test Usage

```python
# Get variant for user
variant = ABTestingService.get_variant('greeting_message', session_id)

# Log conversion
ABTestingService.log_conversion(session_id, 'greeting_message', 'demo_request')
```

---

## 📧 Notifications

### Email Notifications

```python
class NotificationService:
    @staticmethod
    def send_email_alert(lead_data):
        """Send email notification for high-value leads"""

    @staticmethod
    def send_slack_notification(lead_data):
        """Send Slack webhook notification"""

    @staticmethod
    def send_discord_notification(lead_data):
        """Send Discord webhook notification"""
```

### Notification Triggers

- **SQL Lead Captured** (Score ≥ 60)
- **High-Value Behavior** (Demo request, Contact shared)
- **Completed Journey** (All questions answered)

---

## 🚀 Development

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=.

# Run specific test file
python -m pytest tests/test_services.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Database Utilities

```bash
# Check database status
python check_database.py

# View all leads
python -c "from services import LeadService; print(LeadService.get_all_leads())"

# Reset database (development only)
python -c "from database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

---

## 🚀 Deployment

### Production Setup

1. **Environment Configuration**

```bash
# Set production environment variables
export FLASK_ENV=production
export DEBUG=False
export DATABASE_URL=postgresql://user:pass@prod-db:5432/leads
```

2. **Database Migration**

```bash
# Run production migrations
alembic upgrade head
```

3. **WSGI Server (Gunicorn)**

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

4. **Docker Deployment**

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "main:app"]
```

### Environment-Specific Configs

```bash
# Development
DATABASE_URL=postgresql://localhost/lead_dev
DEBUG=True

# Staging
DATABASE_URL=postgresql://staging-db/lead_staging
DEBUG=False

# Production
DATABASE_URL=postgresql://prod-db/lead_production
DEBUG=False
```

---

## 📊 Monitoring & Analytics

### Key Metrics

- **Conversion Rate**: SQL leads / Total sessions
- **Average Score**: Mean score across all leads
- **Completion Rate**: Fully completed sessions percentage
- **Response Time**: Average time between questions

### Health Check Endpoint

```python
@app.route('/health')
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 🤝 Contributing

### Development Workflow

1. **Fork & Clone**

```bash
git clone <your-fork-url>
cd lead-capture-backend
```

2. **Create Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

3. **Make Changes**

```bash
# Make your changes
# Add tests
# Update documentation
```

4. **Test Changes**

```bash
python -m pytest tests/
black .
flake8 .
```

5. **Submit Pull Request**

```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

### Code Standards

- **Python**: Follow PEP 8 style guide
- **Documentation**: Use docstrings for all functions
- **Testing**: Maintain >90% test coverage
- **Commits**: Use conventional commit messages

---

## 📋 API Testing

### Example Requests

#### Start Session

```bash
curl -X POST http://localhost:5000/api/session/start \
  -H "Content-Type: application/json" \
  -d '{"utm_source": "google"}'
```

#### Answer Question

```bash
curl -X POST http://localhost:5000/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_123",
    "question_id": 1,
    "answer_text": "Restaurant"
  }'
```

#### Get Lead Summary

```bash
curl http://localhost:5000/api/lead/summary/sess_123
```

### Response Examples

#### Session Start Response

```json
{
  "session_id": "sess_abc123",
  "message": "Session started successfully",
  "timestamp": "2025-08-13T10:30:00Z"
}
```

#### Lead Summary Response

```json
{
  "session_id": "sess_abc123",
  "lead_data": {
    "name": "John Doe",
    "email": "john@restaurant.com",
    "business_type": "Restaurant",
    "lead_score": 85,
    "classification": "SQL"
  },
  "behaviors": [
    { "action": "session_opened", "score": 5 },
    { "action": "answered_question", "score": 25 },
    { "action": "demo_requested", "score": 15 }
  ]
}
```

---

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Error

```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Test connection
psql -h localhost -U lead_user -d lead_management
```

#### Import Errors

```bash
# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Performance Issues

```bash
# Check database indexes
python check_database.py --analyze

# Monitor memory usage
python -m memory_profiler main.py
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py
```

---

## 📞 Support

For technical support or questions:

- **Documentation**: Check this README and inline code comments
- **Issues**: Create GitHub issue with detailed description
- **Discussions**: Use GitHub Discussions for general questions

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔄 Changelog

### v2.0.0 (2025-08-13)

- **BREAKING**: Migrated from SQLite to PostgreSQL
- **BREAKING**: Removed all frontend components
- **NEW**: Backend-only architecture
- **NEW**: Enhanced API documentation
- **IMPROVED**: Database performance and scalability

### v1.5.0 (Previous)

- Full-stack implementation with frontend
- SQLite database
- Integrated chatbot UI

---

_This documentation is maintained by the development team. Last updated: August 13, 2025_
├── main.py # Flask application and API routes
├── models.py # Database models
├── services.py # Business logic services
├── workflow_config.py # Configuration and scoring rules
├── database.py # Database connection and setup
├── config.py # Application configuration
├── migrate_database.py # Database migration script
├── static/
│ └── lead-capture.html # Frontend chatbot interface
└── lead_management.db # SQLite database

````

## Database Schema

### Leads Table

- `session_id` (unique identifier)
- `utm_source` (traffic source tracking)
- `lead_score` (calculated total score)
- `lead_type` (SQL/MQL/Unqualified)
- Profile fields: `name`, `email`, `phone`, `business_type`, `location`, `staff_size`, `monthly_sales`
- `features_interested` (JSON array)
- Timestamps: `created_at`, `updated_at`

### Answers Table

- `session_id` (foreign key to leads)
- `question_id` (question identifier)
- `answer_text` (user response)
- `time_taken` (response time in seconds)
- `score_earned` (points earned for this answer)

### User Behaviors Table

- `session_id` (foreign key to leads)
- `action` (behavior type)
- `score_change` (points awarded/deducted)
- `behavior_metadata` (additional context)

## Setup Instructions

1. **Install Dependencies**:

   ```bash
   pip install flask flask-cors sqlalchemy
````

2. **Database Setup**:

   ```bash
   python migrate_database.py
   ```

3. **Run Application**:

   ```bash
   python main.py
   ```

4. **Access Chatbot**:
   - Open browser to `http://localhost:5000`
   - Start interacting with the chatbot

## API Usage Examples

### Start Session

```bash
curl -X POST http://localhost:5000/api/session/start \
  -H "Content-Type: application/json" \
  -d '{"utm_source": "google_ads"}'
```

### Log Answer

```bash
curl -X POST http://localhost:5000/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "question_id": 1,
    "answer_text": "Yes, go ahead",
    "time_taken": 5
  }'
```

### Get Lead Summary

```bash
curl http://localhost:5000/api/lead/summary/uuid-here
```

## CRM Export Format

```json
{
  "name": "John Merchant",
  "location": "Mumbai",
  "business_type": "Retail Shop",
  "staff_size": "2–5",
  "monthly_sales": "₹50K–₹2L",
  "features_interested": ["Billing", "QR Payments"],
  "contact_info": "9123456789",
  "email": "john@example.com",
  "phone": "9123456789",
  "lead_score": 75,
  "lead_type": "SQL",
  "utm_source": "google_ads",
  "session_start_time": "2025-08-13T01:30:00Z",
  "assigned_to": "CTL-Team"
}
```

## Configuration Management

All workflow configuration is centralized in `workflow_config.py`:

- **Questions**: Easy to modify question text and options
- **Scoring**: Simple to adjust point values
- **Thresholds**: Easy to change SQL/MQL qualification criteria
- **Products**: Simple to add/remove product options

## Next Steps for Production

1. **Database**: Replace SQLite with PostgreSQL/MySQL
2. **Authentication**: Add API authentication
3. **Rate Limiting**: Implement request throttling
4. **Monitoring**: Add logging and analytics
5. **CRM Integration**: Direct integration with Odoo/HubSpot
6. **WhatsApp Integration**: Add WhatsApp Business API
7. **Multi-language**: Support for regional languages

## Compliance with Requirements

✅ **Backend Only**: No WhatsApp dependency, pure web-based  
✅ **Database Integration**: Ready for external database team  
✅ **Question/Scoring in Code**: All configuration in Python files  
✅ **Web Approach**: Accessible to all users, not just WhatsApp  
✅ **Complete Workflow**: All 7 steps implemented  
✅ **Behavior Tracking**: Comprehensive user interaction logging  
✅ **Lead Qualification**: Automatic SQL/MQL/Unqualified classification  
✅ **CRM Ready**: Structured export format for easy integration
