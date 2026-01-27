# Orbis External API

## Overview

A JSON REST API that allows external applications to create todos and notes in Orbis. Each user can generate an API key that links incoming requests to their account.

---

## Authentication

### API Key System
- Each user can generate **one API key** from their settings
- Key format: `orb_` + 32 random alphanumeric characters (e.g., `orb_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)
- Key is shown **once** upon creation, then stored as a hash
- User can regenerate key (invalidates old one) or revoke it entirely

### Request Authentication
```
Authorization: Bearer orb_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## Endpoints

### Base URL
```
https://your-orbis-domain.com/api/v1
```

### Create Todo
```
POST /api/v1/todos
```

**Request Body:**
```json
{
  "title": "Review registration: user@example.com",
  "due_date": "2026-01-27",
  "priority": 2,
  "tags": ["registrations", "appx"],
  "source_app": "AppX"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Todo title (max 200 chars) |
| `due_date` | string | ❌ | ISO date format (YYYY-MM-DD), defaults to today |
| `priority` | integer | ❌ | 1-3 (1=low, 2=medium, 3=high), defaults to 2 |
| `tags` | array | ❌ | List of tag names (created if don't exist) |
| `source_app` | string | ✅ | Name of the app creating the todo |

**Response (201 Created):**
```json
{
  "success": true,
  "todo": {
    "id": 123,
    "title": "Review registration: user@example.com",
    "due_date": "2026-01-27",
    "priority": 2,
    "description": "Created from AppX"
  }
}
```

---

### Create Note
```
POST /api/v1/notes
```

**Request Body:**
```json
{
  "title": "Support Request #1234",
  "type": "support",
  "content": "User reported issue with login...",
  "source_app": "AppX"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Note title (max 200 chars) |
| `type` | string | ✅ | Note type (must match existing types) |
| `content` | string | ❌ | Plain text content |
| `source_app` | string | ✅ | Name of the app creating the note |

**Note:** Date is automatically added to the title based on the note type settings. The source attribution is appended to content:
```
User reported issue with login...

---
Created from AppX
```

**Response (201 Created):**
```json
{
  "success": true,
  "note": {
    "id": 456,
    "title": "Support Request #1234 - 2026-01-26",
    "type": "support"
  }
}
```

---

## Rate Limiting

- **10 requests per hour** per API key
- Limits reset on the hour

**Headers returned:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1706313600
```

**When exceeded (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 1823
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "error": "Invalid or missing API key"
}
```

### 400 Bad Request
```json
{
  "error": "Validation failed",
  "details": {
    "title": "Title is required",
    "type": "Invalid note type"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 1823
}
```

---

## Admin UI (User Settings)

Add to user settings page (`/settings`):

### API Access Section
```
┌─────────────────────────────────────────────────────────┐
│ API Access                                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ API Key: ●●●●●●●●●●●●●●●●  [Regenerate] [Revoke]       │
│                                                         │
│ Created: 2026-01-15                                     │
│ Last used: 2026-01-26 14:32                            │
│ Requests today: 3 / 10                                  │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ No API key yet?  [Generate API Key]                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**On key generation**, show modal:
```
┌─────────────────────────────────────────────────────────┐
│ Your API Key (copy now - shown only once!)              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ orb_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6     [Copy]        │
│                                                         │
│ Store this securely. You won't be able to see it again.│
│                                                         │
│                                    [I've copied it]     │
└─────────────────────────────────────────────────────────┘
```

---

## Database Changes

### New table: `api_keys`

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | Primary key |
| `user_id` | integer | FK to users (unique - one key per user) |
| `key_hash` | string | Hashed API key |
| `key_prefix` | string | First 8 chars for identification (`orb_a1b2`) |
| `created_at` | datetime | When key was created |
| `last_used_at` | datetime | Last successful request |
| `requests_this_hour` | integer | Counter for rate limiting |
| `hour_started_at` | datetime | When current rate limit window started |

---

## Implementation Tasks

### Phase 1: Database & Model
- [ ] Create `ApiKey` model with fields above
- [ ] Migration for `api_keys` table
- [ ] Key generation/hashing utilities

### Phase 2: API Blueprint
- [ ] Create `blueprints/api.py`
- [ ] Authentication decorator
- [ ] Rate limiting decorator
- [ ] `POST /api/v1/todos` endpoint
- [ ] `POST /api/v1/notes` endpoint
- [ ] Error handling

### Phase 3: Settings UI
- [ ] Add API section to settings page
- [ ] Generate key functionality
- [ ] Regenerate/revoke functionality
- [ ] Display usage stats

### Phase 4: Testing
- [ ] Unit tests for API endpoints
- [ ] Test rate limiting
- [ ] Test authentication

---

## Example: cURL Usage

### Create a todo
```bash
curl -X POST https://orbis.example.com/api/v1/todos \
  -H "Authorization: Bearer orb_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review registration: user@example.com",
    "source_app": "MyApp",
    "priority": 3,
    "tags": ["urgent", "registrations"]
  }'
```

### Create a note
```bash
curl -X POST https://orbis.example.com/api/v1/notes \
  -H "Authorization: Bearer orb_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Support Request",
    "type": "support",
    "content": "Customer needs help with...",
    "source_app": "SupportDesk"
  }'
```

---

## Security Considerations

1. **HTTPS only** - API should reject non-HTTPS requests in production
2. **Key hashing** - Store keys as hashes (SHA-256), never plain text
3. **Rate limiting** - Prevents abuse and DoS
4. **Input validation** - Sanitize all input, enforce max lengths
5. **Logging** - Log all API requests for audit trail
