# External API Integration Documentation

## Overview

The Storm SaaS Platform provides comprehensive external API integration capabilities designed for financial and medical applications. This documentation covers authentication, endpoints, data security, webhooks, and best practices for integrating with external systems.

## Table of Contents

1. [Authentication](#authentication)
2. [API Endpoints](#api-endpoints)
3. [Data Security & Privacy](#data-security--privacy)
4. [Webhooks](#webhooks)
5. [Rate Limiting](#rate-limiting)
6. [Error Handling](#error-handling)
7. [SDKs & Examples](#sdks--examples)
8. [Compliance](#compliance)

## Authentication

### API Key Authentication

All external API requests require authentication using API keys.

```http
GET /api/v1/external/users/123
Authorization: Bearer your-api-key-here
Content-Type: application/json
```

### JWT Token Authentication

For user-specific operations, JWT tokens can be used:

```http
POST /api/v1/external/users
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### Permission-Based Access Control

API access is controlled through a role-based permission system:

- **API_INTEGRATION**: Basic external API access
- **EXTERNAL_SERVICE**: Enhanced integration capabilities
- **ADMIN**: Full administrative access

## API Endpoints

### Base URL

```
https://your-storm-instance.com/api/v1/external
```

### External Integration Management

#### Create Integration

```http
POST /integrations
Content-Type: application/json

{
  "name": "MyFinancialApp",
  "integration_type": "financial",
  "description": "Integration with financial planning application",
  "webhook_url": "https://myapp.com/webhooks/storm",
  "webhook_secret": "your-webhook-secret",
  "api_key": "your-external-api-key",
  "is_active": true
}
```

**Response:**
```json
{
  "id": 1,
  "name": "MyFinancialApp",
  "integration_type": "financial",
  "description": "Integration with financial planning application",
  "webhook_url": "https://myapp.com/webhooks/storm",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### List Integrations

```http
GET /integrations
```

#### Get Integration

```http
GET /integrations/{integration_id}
```

#### Update Integration

```http
PUT /integrations/{integration_id}
Content-Type: application/json

{
  "description": "Updated description",
  "is_active": false
}
```

#### Delete Integration

```http
DELETE /integrations/{integration_id}
```

### User Management

#### Create External User

```http
POST /users
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "john_doe",
  "full_name": "John Doe",
  "role": "API_INTEGRATION",
  "external_id": "ext_user_123",
  "integration_source": "MyFinancialApp",
  "metadata": {
    "department": "Finance",
    "employee_id": "EMP001"
  }
}
```

**Response:**
```json
{
  "id": 123,
  "email": "u***@example.com",
  "username": "john_doe",
  "full_name": "John Doe",
  "role": "API_INTEGRATION",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "external_id": "ext_user_123",
  "integration_source": "MyFinancialApp",
  "permissions": ["user:read", "project:read"],
  "subscription_plan": "professional"
}
```

#### Get User

```http
GET /users/{user_id}
```

#### Update User

```http
PUT /users/{user_id}
Content-Type: application/json

{
  "full_name": "John Smith",
  "metadata": {
    "department": "Engineering"
  }
}
```

### Project Management

#### Create External Project

```http
POST /projects
Content-Type: application/json

{
  "name": "Financial Dashboard",
  "description": "Customer financial analytics dashboard",
  "external_id": "proj_fin_001",
  "integration_source": "MyFinancialApp",
  "metadata": {
    "client_id": "CLIENT_123",
    "budget": 50000
  }
}
```

### Generic API Proxy

#### Make External API Call

```http
POST /api-call
Content-Type: application/json

{
  "method": "POST",
  "endpoint": "https://api.external-service.com/v1/data",
  "headers": {
    "Authorization": "Bearer external-token",
    "X-Custom-Header": "value"
  },
  "query_params": {
    "limit": 100,
    "offset": 0
  },
  "body": {
    "filter": "active",
    "fields": ["id", "name", "status"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "results": [...],
    "total": 150
  },
  "response_time": 0.245
}
```

### Data Synchronization

#### Sync Data

```http
POST /sync
Content-Type: application/json

{
  "entity_type": "user",
  "entity_id": 123,
  "sync_direction": "bidirectional",
  "field_mappings": {
    "email": "email_address",
    "full_name": "display_name",
    "metadata.employee_id": "emp_id"
  },
  "conflict_resolution": "external_wins"
}
```

**Response:**
```json
{
  "sync_id": "sync_uuid_123",
  "entity_type": "user",
  "entity_id": 123,
  "status": "pending",
  "started_at": "2024-01-15T10:30:00Z"
}
```

## Data Security & Privacy

### Field-Level Encryption

Sensitive data is automatically encrypted at rest using AES-256 encryption:

- **PII Fields**: email, phone, SSN, address
- **Financial Fields**: account numbers, routing numbers, credit card data
- **Medical Fields**: patient IDs, medical record numbers, health data

### Data Masking

Data is automatically masked based on integration type:

#### Financial Integration
```json
{
  "email": "j***@example.com",
  "phone": "***-***-1234",
  "account_number": "****-****-****-1234"
}
```

#### Medical Integration
```json
{
  "email": "j***@example.com",
  "patient_id": "PAT***123",
  "medical_record": "[REDACTED]"
}
```

### Data Sensitivity Levels

- **PUBLIC**: Non-sensitive data (names, general info)
- **INTERNAL**: Internal business data
- **CONFIDENTIAL**: Sensitive personal/financial data
- **RESTRICTED**: Highly sensitive medical/legal data

## Webhooks

### Webhook Events

Storm automatically sends webhooks for the following events:

- `user.created`
- `user.updated`
- `user.deleted`
- `project.created`
- `project.updated`
- `project.deleted`
- `api_key.created`
- `api_key.deleted`
- `subscription.updated`
- `usage.threshold_reached`

### Webhook Payload

```json
{
  "event": "user.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "id": 123,
    "email": "u***@example.com",
    "username": "john_doe",
    "external_id": "ext_user_123",
    "integration_source": "MyFinancialApp"
  },
  "integration_id": 1,
  "signature": "sha256=abc123..."
}
```

### Webhook Security

Webhooks are secured using HMAC-SHA256 signatures:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Test Webhook

```http
POST /webhooks/test
Content-Type: application/json

{
  "integration_id": 1
}
```

## Rate Limiting

### Rate Limits by Plan

| Plan | Requests/Hour | Burst Limit |
|------|---------------|-------------|
| Basic | 1,000 | 100 |
| Professional | 10,000 | 500 |
| Enterprise | 100,000 | 2,000 |

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
X-RateLimit-Retry-After: 3600
```

### Rate Limit Exceeded

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": "Rate limit exceeded",
  "message": "API rate limit exceeded. Try again in 3600 seconds.",
  "retry_after": 3600
}
```

## Error Handling

### Standard Error Response

```json
{
  "error": "validation_error",
  "message": "Invalid input data",
  "details": {
    "field": "email",
    "code": "invalid_format",
    "message": "Email format is invalid"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Server Error |

## SDKs & Examples

### Python SDK Example

```python
from storm_api import StormClient

# Initialize client
client = StormClient(
    api_key="your-api-key",
    base_url="https://your-storm-instance.com"
)

# Create integration
integration = client.integrations.create({
    "name": "MyApp",
    "integration_type": "financial",
    "webhook_url": "https://myapp.com/webhooks"
})

# Create user
user = client.users.create({
    "email": "user@example.com",
    "username": "john_doe",
    "external_id": "ext_123"
})

# Sync data
sync_result = client.sync.start({
    "entity_type": "user",
    "entity_id": user.id,
    "sync_direction": "bidirectional"
})
```

### JavaScript SDK Example

```javascript
import { StormClient } from '@storm/api-client';

const client = new StormClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://your-storm-instance.com'
});

// Create integration
const integration = await client.integrations.create({
  name: 'MyApp',
  integrationType: 'medical',
  webhookUrl: 'https://myapp.com/webhooks'
});

// Get user with error handling
try {
  const user = await client.users.get(123);
  console.log('User:', user);
} catch (error) {
  if (error.status === 404) {
    console.log('User not found');
  } else {
    console.error('API Error:', error.message);
  }
}
```

### cURL Examples

#### Create User

```bash
curl -X POST https://your-storm-instance.com/api/v1/external/users \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "john_doe",
    "full_name": "John Doe",
    "external_id": "ext_123"
  }'
```

#### Get Integration

```bash
curl -X GET https://your-storm-instance.com/api/v1/external/integrations/1 \
  -H "Authorization: Bearer your-api-key"
```

## Compliance

### HIPAA Compliance (Medical Integrations)

- All PHI is encrypted at rest and in transit
- Audit logs track all access to medical data
- Data retention policies comply with HIPAA requirements
- Business Associate Agreements (BAA) available

### PCI DSS Compliance (Financial Integrations)

- Credit card data is tokenized and encrypted
- PCI DSS Level 1 compliant infrastructure
- Regular security assessments and penetration testing
- Secure key management practices

### GDPR Compliance

- Data subject rights supported (access, rectification, erasure)
- Privacy by design principles implemented
- Data processing agreements available
- Cross-border data transfer safeguards

### SOC 2 Type II

- Annual SOC 2 Type II audits
- Security, availability, and confidentiality controls
- Incident response procedures
- Change management processes

## Support

### API Support

- **Email**: api-support@storm-platform.com
- **Documentation**: https://docs.storm-platform.com
- **Status Page**: https://status.storm-platform.com
- **Community Forum**: https://community.storm-platform.com

### SLA

- **Uptime**: 99.9% guaranteed
- **Response Time**: < 200ms average
- **Support Response**: < 4 hours for critical issues

### Changelog

Stay updated with API changes:
- **RSS Feed**: https://docs.storm-platform.com/changelog.rss
- **Webhook**: Subscribe to `api.version.updated` events
- **Email Notifications**: Available in developer dashboard

---

*Last Updated: January 2024*
*API Version: v1.0*