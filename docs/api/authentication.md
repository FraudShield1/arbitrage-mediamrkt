# Authentication API Documentation

## Overview

The Authentication API provides secure user management and JWT-based authentication for the Cross-Market Arbitrage Tool. It supports role-based access control with admin and regular user permissions, password management, and user lifecycle operations.

**Base Path:** `/api/v1/auth`

## Authentication Flow

1. **Login** with username/password to receive JWT access token
2. **Include token** in `Authorization: Bearer <token>` header for subsequent requests
3. **Refresh token** before expiration (30 minutes default)
4. **Logout** (client-side token removal)

## Endpoints

### POST /api/v1/auth/login

Authenticate user and receive access token.

#### Request Body

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User's username |
| `password` | string | Yes | User's password |

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secure_password"}'
```

#### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@arbitrage-tool.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-15T10:30:00Z"
  }
}
```

### POST /api/v1/auth/register

Register a new user (admin only).

#### Request Body

```json
{
  "username": "new_user",
  "email": "user@example.com",
  "password": "secure_password",
  "role": "user"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username (3-50 chars) |
| `email` | string | Yes | Valid email address |
| `password` | string | Yes | Password (min 8 chars) |
| `role` | string | No | User role (admin, user) - default: user |

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst01",
    "email": "analyst@company.com",
    "password": "SecurePass123!",
    "role": "user"
  }'
```

#### Response

```json
{
  "id": 5,
  "username": "analyst01",
  "email": "analyst@company.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": null
}
```

### POST /api/v1/auth/refresh

Refresh access token using current valid token.

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Authorization: Bearer YOUR_CURRENT_TOKEN"
```

#### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET /api/v1/auth/me

Get current user information.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@arbitrage-tool.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-10T15:20:00Z",
  "last_login": "2024-01-15T10:30:00Z",
  "login_count": 47,
  "preferences": {
    "notification_email": true,
    "notification_telegram": true,
    "alert_threshold": 30.0
  }
}
```

### PUT /api/v1/auth/me

Update current user information.

#### Request Body

```json
{
  "email": "new_email@example.com"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | No | New email address |
| `role` | string | No | New role (admin only) |
| `is_active` | boolean | No | Active status (admin only) |

#### Example Request

```bash
curl -X PUT "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "updated_email@example.com"}'
```

#### Response

```json
{
  "id": 1,
  "username": "admin",
  "email": "updated_email@example.com",
  "role": "admin",
  "is_active": true,
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### POST /api/v1/auth/change-password

Change user password.

#### Request Body

```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_password` | string | Yes | Current password for verification |
| `new_password` | string | Yes | New password (min 8 chars) |

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "old_password",
    "new_password": "NewSecurePass123!"
  }'
```

#### Response

```json
{
  "message": "Password changed successfully"
}
```

### GET /api/v1/auth/users

List all users (admin only).

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `size` | integer | 20 | Items per page |
| `role` | string | null | Filter by role |
| `is_active` | boolean | null | Filter by active status |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/auth/users?role=user&is_active=true" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Response

```json
{
  "users": [
    {
      "id": 2,
      "username": "analyst01",
      "email": "analyst@company.com",
      "role": "user",
      "is_active": true,
      "created_at": "2024-01-10T08:00:00Z",
      "last_login": "2024-01-15T09:15:00Z",
      "login_count": 23
    },
    {
      "id": 3,
      "username": "trader02",
      "email": "trader@company.com",
      "role": "user",
      "is_active": true,
      "created_at": "2024-01-12T10:30:00Z",
      "last_login": "2024-01-15T10:00:00Z",
      "login_count": 15
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 12,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### GET /api/v1/auth/users/{user_id}

Get specific user by ID (admin only).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | User ID to retrieve |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/auth/users/2" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Response

```json
{
  "id": 2,
  "username": "analyst01",
  "email": "analyst@company.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-10T08:00:00Z",
  "updated_at": "2024-01-14T16:20:00Z",
  "last_login": "2024-01-15T09:15:00Z",
  "login_count": 23,
  "preferences": {
    "notification_email": true,
    "notification_telegram": false,
    "alert_threshold": 50.0
  }
}
```

### PUT /api/v1/auth/users/{user_id}

Update user by ID (admin only).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | User ID to update |

#### Request Body

```json
{
  "email": "new_email@example.com",
  "role": "admin",
  "is_active": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | No | New email address |
| `role` | string | No | New role (admin, user) |
| `is_active` | boolean | No | Active status |

#### Example Request

```bash
curl -X PUT "http://localhost:8000/api/v1/auth/users/2" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin",
    "is_active": true
  }'
```

#### Response

```json
{
  "id": 2,
  "username": "analyst01",
  "email": "analyst@company.com",
  "role": "admin",
  "is_active": true,
  "updated_at": "2024-01-15T10:40:00Z"
}
```

### DELETE /api/v1/auth/users/{user_id}

Delete user by ID (admin only).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | User ID to delete |

#### Example Request

```bash
curl -X DELETE "http://localhost:8000/api/v1/auth/users/5" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Response

```json
{
  "message": "User 5 deleted successfully"
}
```

## Data Models

### User Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique user identifier |
| `username` | string | Unique username |
| `email` | string | User email address |
| `role` | string | User role (admin, user) |
| `is_active` | boolean | Account active status |
| `created_at` | datetime | Account creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `last_login` | datetime | Last login timestamp |
| `login_count` | integer | Total login count |
| `preferences` | object | User preferences |

### User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | System administrator | Full access to all endpoints and user management |
| `user` | Regular user | Access to products, alerts, and own profile |

### JWT Token Structure

```json
{
  "sub": "1",
  "username": "admin",
  "role": "admin",
  "iat": 1642345200,
  "exp": 1642347000
}
```

## Security Features

### Password Requirements
- Minimum 8 characters
- Must contain uppercase, lowercase, number, and special character
- Cannot be common passwords
- Cannot be similar to username or email

### Token Security
- JWT tokens with HS256 signing
- 30-minute expiration time
- Refresh token mechanism
- Secure HTTP-only cookies (optional)

### Rate Limiting
- Login attempts: 5 per minute per IP
- Token refresh: 10 per minute per user
- General auth endpoints: 20 per minute per user

## Error Responses

### 401 Unauthorized
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Invalid username or password",
    "status_code": 401
  }
}
```

### 403 Forbidden
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Account is inactive",
    "status_code": 403
  }
}
```

### 409 Conflict
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Username already exists",
    "status_code": 409
  }
}
```

### 422 Validation Error
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Request validation failed",
    "details": [
      {
        "loc": ["body", "password"],
        "msg": "Password must be at least 8 characters",
        "type": "value_error"
      }
    ]
  }
}
```

## Usage Examples

### Complete Authentication Flow

```bash
# 1. Login
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secure_password"}')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# 2. Use token for API calls
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer $TOKEN"

# 3. Refresh token before expiry
NEW_TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.access_token')
```

### User Management (Admin)

```bash
# Create new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_analyst",
    "email": "analyst@company.com",
    "password": "SecurePass123!",
    "role": "user"
  }'

# List all users
curl -X GET "http://localhost:8000/api/v1/auth/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Promote user to admin
curl -X PUT "http://localhost:8000/api/v1/auth/users/5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

### Password Management

```bash
# Change own password
curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "old_password",
    "new_password": "NewSecurePass123!"
  }'
```

## Best Practices

1. **Store tokens securely** - Use secure storage, never in localStorage
2. **Implement refresh logic** - Refresh tokens before expiry
3. **Handle token expiry gracefully** - Redirect to login on 401 errors
4. **Use HTTPS in production** - Never send tokens over HTTP
5. **Implement logout** - Clear tokens on client side
6. **Monitor failed attempts** - Log and alert on suspicious activity

---

**Last Updated:** January 2024 