# Chatbot Cloud API Documentation

This document provides detailed information about all API endpoints available in your chatbot_cloud project, including their HTTP methods, paths, descriptions, authentication requirements, and sample request bodies for testing in Postman.

---

## Table of Contents

- [Public APIs](#public-apis)
- [Ticket Escalation & SLA APIs](#ticket-escalation--sla-apis)
- [Odoo Integration APIs](#odoo-integration-apis)
- [Urban Vyapari Integration](#urban-vyapari-integration)
- [Admin APIs](#admin-apis)
- [Super Admin APIs](#super-admin-apis)

---

## Public APIs

### 1. Get All Support Categories

- **Method:** GET
- **Path:** `/api/categories`
- **Auth:** None
- **Description:** Returns all support categories.
- **Request Body:** _None_

### 2. Get Common Queries for Category

- **Method:** GET
- **Path:** `/api/common-queries/<category_id>`
- **Auth:** None
- **Description:** Returns common queries for a given category.
- **Request Body:** _None_

### 3. Create New Ticket

- **Method:** POST
- **Path:** `/api/tickets`
- **Auth:** None
- **Description:** Creates a new support ticket.
- **Request Body (JSON):**

```
{
  "name": "John Doe",
  "email": "john@example.com",
  "category_id": 1,
  "subject": "Issue with product",
  "message": "Describe your issue here",
  "priority": "medium",
  "organization": "Acme Corp"
}
```

### 4. Create Ticket with File Attachment

- **Method:** POST
- **Path:** `/api/tickets/with-attachment`
- **Auth:** None
- **Description:** Creates a new ticket with a file attachment.
- **Request Body (form-data):**
  - `name`: string
  - `email`: string
  - `category_id`: integer
  - `subject`: string
  - `message`: string
  - `file`: file (optional)

### 5. Get Ticket Details

- **Method:** GET
- **Path:** `/api/tickets/<ticket_id>`
- **Auth:** None
- **Description:** Returns details for a specific ticket.
- **Request Body:** _None_

### 6. Get/Add Messages for Ticket

- **Method:** GET, POST
- **Path:** `/api/tickets/<ticket_id>/messages`
- **Auth:** None
- **Description:**
  - **GET:** Returns all messages for a ticket.
  - **POST:** Adds a message to a ticket.
- **Request Body (POST, JSON):**

```
{
  "user_id": 123,
  "content": "Your message here",
  "is_admin": false
}
```

### 7. Add Message with Attachment

- **Method:** POST
- **Path:** `/api/tickets/<ticket_id>/messages/with-attachment`
- **Auth:** None
- **Description:** Adds a message with an optional file attachment to a ticket.
- **Request Body (form-data):**
  - `user_id`: integer
  - `content`: string
  - `is_admin`: boolean (as string, e.g., "false")
  - `file`: file (optional)

### 8. Upload File

- **Method:** POST
- **Path:** `/api/upload`
- **Auth:** None
- **Description:** Uploads a file and returns file info.
- **Request Body (form-data):**
  - `file`: file (required)

### 9. Submit Feedback/Rating

- **Method:** POST
- **Path:** `/api/feedback`
- **Auth:** None
- **Description:** Submits feedback for a ticket.
- **Request Body (JSON):**

```
{
  "ticket_id": 123,
  "rating": 5,
  "feedback": "Great support!"
}
```

### 10. Test System Health

- **Method:** GET
- **Path:** `/api/database/test`
- **Auth:** None
- **Description:** Tests database connection and returns status.
- **Request Body:** _None_

### 11. Health Check

- **Method:** GET
- **Path:** `/health`
- **Auth:** None
- **Description:** Returns health status of the system.
- **Request Body:** _None_

### 12. Download Uploaded File

- **Method:** GET
- **Path:** `/static/uploads/<filename>`
- **Auth:** None
- **Description:** Downloads a previously uploaded file.
- **Request Body:** _None_

---

## Ticket Escalation & SLA APIs

### 13. Escalate a Ticket (Admin)

- **Method:** POST
- **Path:** `/api/tickets/<ticket_id>/escalate`
- **Auth:** Admin
- **Description:** Escalates a ticket to a higher support level.
- **Request Body (JSON):**

```
{
  "escalationReason": "Manual escalation",
  "escalatedTo": "admin_01",
  "autoEscalated": false,
  "escalationLevel": 2
}
```

### 14. Get SLA Status for a Ticket

- **Method:** GET
- **Path:** `/api/tickets/<ticket_id>/sla-status`
- **Auth:** None
- **Description:** Returns SLA status for a ticket.
- **Request Body:** _None_

### 15. SLA Monitoring Dashboard (Admin)

- **Method:** GET
- **Path:** `/api/tickets/sla-monitor`
- **Auth:** Admin
- **Description:** Returns SLA monitoring dashboard data.
- **Request Body:** _None_

### 16. Get Escalation History for a Ticket

- **Method:** GET
- **Path:** `/api/tickets/<ticket_id>/escalation-history`
- **Auth:** None
- **Description:** Returns escalation history for a ticket.
- **Request Body:** _None_

---

## Odoo Integration APIs

### 17. Test Odoo Connection

- **Method:** GET
- **Path:** `/api/odoo/test-connection`
- **Auth:** None
- **Description:** Tests Odoo connection and returns status.
- **Request Body:** _None_

### 18. Get/Create Odoo Customers

- **Method:** GET, POST
- **Path:** `/api/odoo/customers`
- **Auth:** None
- **Description:**
  - **GET:** Returns Odoo customers.
  - **POST:** Creates a new Odoo customer.
- **Request Body (POST, JSON):**

```
{
  "name": "Customer Name",
  "email": "customer@example.com",
  "phone": "1234567890"
}
```

### 19. Get/Create Odoo Tickets

- **Method:** GET, POST
- **Path:** `/api/odoo/tickets`
- **Auth:** None
- **Description:**
  - **GET:** Returns Odoo tickets.
  - **POST:** Creates a new Odoo ticket.
- **Request Body (POST, JSON):**

```
{
  "name": "Ticket Subject",
  "description": "Ticket description",
  "partner_id": 1,
  "priority": "1"
}
```

### 20. Update/Delete Odoo Ticket

- **Method:** PUT, DELETE
- **Path:** `/api/odoo/tickets/<ticket_id>`
- **Auth:** None
- **Description:** Updates or deletes an Odoo ticket.
- **Request Body (PUT, JSON):**

```
{
  "description": "Updated description",
  "priority": "2"
}
```

### 21. Generic Odoo Model Method Call

- **Method:** POST
- **Path:** `/api/odoo/<model>/<method>`
- **Auth:** None
- **Description:** Calls any Odoo model method.
- **Request Body (JSON):**

```
{
  "args": [],
  "kwargs": {}
}
```

### 22. Get Odoo Model Fields

- **Method:** GET
- **Path:** `/api/odoo/<model>/fields_get`
- **Auth:** None
- **Description:** Returns metadata for an Odoo model.
- **Request Body:** _None_

---

## Urban Vyapari Integration

### 23. Generate Urban Vyapari Access Token

- **Method:** POST
- **Path:** `/api/generate-uv-token`
- **Auth:** None
- **Description:** Generates an access token for Urban Vyapari integration.
- **Request Body (JSON):**

```
{
  "uv_api_key": "your-uv-api-key",
  "admin_id": "admin123",
  "admin_name": "Admin Name",
  "admin_email": "admin@example.com"
}
```

---

## Admin APIs

### 24. Dashboard Statistics

- **Method:** GET
- **Path:** `/api/admin/dashboard-stats`
- **Auth:** Admin
- **Description:** Returns dashboard statistics.
- **Request Body:** _None_

### 25. Recent Activity

- **Method:** GET
- **Path:** `/api/admin/recent-activity`
- **Auth:** Admin
- **Description:** Returns recent activity.
- **Request Body:** _None_

### 26. All Tickets (Admin View)

- **Method:** GET
- **Path:** `/api/admin/tickets`
- **Auth:** Admin
- **Description:** Returns all tickets for admin.
- **Request Body:** _None_

### 27. Ticket Details (Admin View)

- **Method:** GET
- **Path:** `/api/admin/tickets/<ticket_id>`
- **Auth:** Admin
- **Description:** Returns ticket details for admin.
- **Request Body:** _None_

### 28. Update Ticket Status

- **Method:** PUT
- **Path:** `/api/admin/tickets/<ticket_id>/status`
- **Auth:** Admin
- **Description:** Updates the status of a ticket.
- **Request Body (JSON):**

```
{
  "status": "resolved",
  "message": "Your issue has been resolved."
}
```

### 29. Active Conversations

- **Method:** GET
- **Path:** `/api/admin/active-conversations`
- **Auth:** Admin
- **Description:** Returns active conversations.
- **Request Body:** _None_

### 30. Analytics Data

- **Method:** GET
- **Path:** `/api/admin/analytics`
- **Auth:** Admin
- **Description:** Returns analytics data.
- **Request Body:** _None_

---

## Super Admin APIs

### 31. Get All Partners

- **Method:** GET
- **Path:** `/super-admin/api/partners`
- **Auth:** Super Admin
- **Description:** Returns all partners with statistics.
- **Request Body:** _None_

### 32. Create Partner

- **Method:** POST
- **Path:** `/super-admin/api/partners`
- **Auth:** Super Admin
- **Description:** Creates a new partner.
- **Request Body (JSON):**

```
{
  "name": "Partner Name",
  "partner_type": "ICP",
  "email": "partner@example.com",
  "contact_person": "Contact Name",
  "phone": "1234567890",
  "webhook_url": "https://webhook.url/",
  "escalation_settings": {},
  "sla_settings": {}
}
```

### 33. Update Partner

- **Method:** PUT
- **Path:** `/super-admin/api/partners/<partner_id>`
- **Auth:** Super Admin
- **Description:** Updates an existing partner.
- **Request Body (JSON):**

```
{
  "name": "Updated Name",
  "partner_type": "YCP",
  "email": "new@example.com",
  "contact_person": "New Contact",
  "phone": "9876543210",
  "status": "active",
  "webhook_url": "https://newwebhook.url/",
  "escalation_settings": {},
  "sla_settings": {}
}
```

### 34. Delete Partner

- **Method:** DELETE
- **Path:** `/super-admin/api/partners/<partner_id>`
- **Auth:** Super Admin
- **Description:** Deletes a partner.
- **Request Body:** _None_

### 35. Escalation Dashboard

- **Method:** GET
- **Path:** `/super-admin/api/escalation/dashboard`
- **Auth:** Super Admin
- **Description:** Returns escalation dashboard data.
- **Request Body:** _None_

### 36. Force Escalate Ticket

- **Method:** POST
- **Path:** `/super-admin/api/escalation/force/<ticket_id>`
- **Auth:** Super Admin
- **Description:** Manually force escalate a ticket.
- **Request Body (JSON):**

```
{
  "level": 2,
  "comment": "Escalate to YCP partner"
}
```

### 37. Get Ticket Timeline

- **Method:** GET
- **Path:** `/super-admin/api/logs/timeline/<ticket_id>`
- **Auth:** Super Admin
- **Description:** Returns the complete timeline for a ticket (status changes, SLA events, messages).
- **Request Body:** _None_

### 38. Search Workflow Logs

- **Method:** GET
- **Path:** `/super-admin/api/logs/search`
- **Auth:** Super Admin
- **Description:** Search workflow logs with filters.
- **Request Body (Query Params):**
  - `ticket_id`, `date_from`, `date_to`, `escalation_level`, `status`, `page`, `per_page`

### 39. Get Audit Logs

- **Method:** GET
- **Path:** `/super-admin/api/audit/logs`
- **Auth:** Super Admin
- **Description:** Returns audit logs with filters.
- **Request Body (Query Params):**
  - `action`, `resource_type`, `user_type`, `date_from`, `date_to`, `page`, `per_page`

### 40. Export Reports

- **Method:** POST
- **Path:** `/super-admin/api/reports/export`
- **Auth:** Super Admin
- **Description:** Exports reports as CSV.
- **Request Body (JSON):**

```
{
  "type": "tickets", // or "sla_compliance"
  "date_from": "2025-07-01",
  "date_to": "2025-07-30",
  "filters": {}
}
```

### 41. Get/Update Bot Configuration

- **Method:** GET, POST
- **Path:** `/super-admin/api/bot/config`
- **Auth:** Super Admin
- **Description:** Get or update bot configuration.
- **Request Body (POST, JSON):**

```
{
  "name": "Default Bot",
  "bot_type": "dialogflow",
  "api_endpoint": "https://api.dialogflow.com/",
  "api_key": "your-api-key",
  "config_data": {},
  "fallback_to_human": true,
  "confidence_threshold": 0.7
}
```

### 42. Dashboard Metrics (Legacy & Fixed)

- **Method:** GET
- **Path:** `/super-admin/api/dashboard-metrics`, `/super-admin/api/dashboard/metrics`
- **Auth:** Super Admin
- **Description:** Returns dashboard metrics.
- **Request Body:** _None_

### 43. Critical Alerts

- **Method:** GET
- **Path:** `/super-admin/api/critical-alerts`, `/super-admin/api/alerts/critical`
- **Auth:** Super Admin
- **Description:** Returns critical system alerts.
- **Request Body:** _None_

### 44. Workflow Logs

- **Method:** GET
- **Path:** `/super-admin/api/workflow-logs`
- **Auth:** Super Admin
- **Description:** Returns workflow logs.
- **Request Body:** _None_

### 45. Audit Logs (Alternative)

- **Method:** GET
- **Path:** `/super-admin/api/audit-logs`
- **Auth:** Super Admin
- **Description:** Returns audit logs (alternative endpoint).
- **Request Body:** _None_

### 46. Users List

- **Method:** GET
- **Path:** `/super-admin/api/users`
- **Auth:** Super Admin
- **Description:** Returns users list for audit log filters.
- **Request Body:** _None_

### 47. Security Alerts

- **Method:** GET
- **Path:** `/super-admin/api/security-alerts`
- **Auth:** Super Admin
- **Description:** Returns security alerts.
- **Request Body:** _None_

### 48. Bot Config (Alternative)

- **Method:** GET, POST
- **Path:** `/super-admin/api/bot-config`
- **Auth:** Super Admin
- **Description:** Get or save bot configuration (alternative endpoint).
- **Request Body (POST, JSON):**

```
{
  "bot_type": "dialogflow",
  "confidence_threshold": 0.7,
  "fallback_to_human": true,
  "enabled": true
}
```

### 49. Bot Status

- **Method:** GET
- **Path:** `/super-admin/api/bot-status`
- **Auth:** Super Admin
- **Description:** Returns bot status and performance metrics.
- **Request Body:** _None_

### 50. Test Bot Connection

- **Method:** POST
- **Path:** `/super-admin/api/test-bot-connection`
- **Auth:** Super Admin
- **Description:** Tests bot connection.
- **Request Body:** _None_

### 51. Test Bot Message

- **Method:** POST
- **Path:** `/super-admin/api/test-bot-message`
- **Auth:** Super Admin
- **Description:** Tests bot with a message.
- **Request Body (JSON):**

```
{
  "message": "Hello bot!"
}
```

### 52. Get Ticket Details (Workflow Logs)

- **Method:** GET
- **Path:** `/super-admin/api/tickets/<ticket_id>`
- **Auth:** Super Admin
- **Description:** Returns ticket details for workflow logs.
- **Request Body:** _None_

### 53. SLA Overview (Legacy & Current)

- **Method:** GET
- **Path:** `/super-admin/api/sla/overview_legacy`, `/super-admin/api/sla/overview`
- **Auth:** Super Admin
- **Description:** Returns SLA overview data.
- **Request Body:** _None_

### 54. Detailed SLA Data

- **Method:** GET
- **Path:** `/super-admin/api/sla/detailed`
- **Auth:** Super Admin
- **Description:** Returns detailed SLA data for a specific priority or time range.
- **Request Body (Query Params):**
  - `priority`, `days`

### 55. SLA Analytics

- **Method:** GET
- **Path:** `/super-admin/api/sla/analytics`
- **Auth:** Super Admin
- **Description:** Returns SLA analytics and trends.
- **Request Body (Query Params):**
  - `days`

### 56. Debug Database

- **Method:** GET
- **Path:** `/super-admin/api/debug/database`
- **Auth:** Super Admin
- **Description:** Debugs database connection and status.
- **Request Body:** _None_

### 57. Test Force Escalate

- **Method:** POST
- **Path:** `/super-admin/api/escalation/test-force/<ticket_id>`
- **Auth:** Super Admin
- **Description:** Test force escalate a ticket (for testing only).
- **Request Body (JSON):**

```
{
  "level": 1,
  "comment": "Test escalation"
}
```

---

**Note:** For all endpoints that require authentication, ensure you are logged in as an admin or super admin before making requests in Postman. For file uploads, use `form-data` in Postman and select the file type for the file field.

---

_Document generated on July 30, 2025._
