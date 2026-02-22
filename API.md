# API Documentation

Complete REST API reference for Bug Bounty Automation Platform.

## Base URL

```
http://localhost:5000/api
```

## Response Format

All API responses follow this format:

```json
{
  "success": true,
  "data": { ... }
}
```

Error responses:

```json
{
  "success": false,
  "error": "Error message"
}
```

## Endpoints

### Health Check

#### GET /api/health

Check API health status.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0-phase1"
  }
}
```

---

### Targets

#### GET /api/targets

List all targets.

**Query Parameters:**
- `status` (optional): Filter by status (active, paused)

**Example:**
```bash
curl http://localhost:5000/api/targets
curl http://localhost:5000/api/targets?status=active
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Example Corp",
      "base_domain": "example.com",
      "program_platform": "HackerOne",
      "status": "active",
      "description": "Main target",
      "notes": null,
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:00:00",
      "scope_count": 5,
      "attack_profile_count": 6,
      "scan_result_count": 0
    }
  ]
}
```

#### POST /api/targets

Create a new target.

**Request Body:**
```json
{
  "name": "Example Corp",
  "base_domain": "example.com",
  "program_platform": "HackerOne",
  "description": "Main target",
  "notes": "Be careful with rate limits"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Corp",
    "base_domain": "example.com",
    "program_platform": "HackerOne"
  }'
```

**Response:** (201 Created)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Example Corp",
    "base_domain": "example.com",
    ...
  }
}
```

#### GET /api/targets/{id}

Get a specific target.

**Example:**
```bash
curl http://localhost:5000/api/targets/1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Example Corp",
    ...
  }
}
```

#### PUT /api/targets/{id}

Update a target.

**Request Body:**
```json
{
  "status": "paused",
  "notes": "Updated notes"
}
```

**Example:**
```bash
curl -X PUT http://localhost:5000/api/targets/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "paused"}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "paused",
    ...
  }
}
```

#### DELETE /api/targets/{id}

Delete a target (cascades to scope, attack profiles, and results).

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/targets/1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "deleted": true
  }
}
```

---

### Scope

#### GET /api/targets/{id}/scope

Get all scope entries for a target.

**Example:**
```bash
curl http://localhost:5000/api/targets/1/scope
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "target_id": 1,
      "scope_type": "domain",
      "value": "example.com",
      "in_scope": true,
      "notes": null,
      "priority": 5,
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:00:00"
    }
  ]
}
```

#### POST /api/targets/{id}/scope

Add a scope entry to a target.

**Request Body:**
```json
{
  "scope_type": "domain",
  "value": "example.com",
  "in_scope": true,
  "notes": "Main domain",
  "priority": 5
}
```

**Scope Types:**
- `domain`: Single domain
- `wildcard`: Wildcard domain (*.example.com)
- `url`: Specific URL
- `api`: API endpoint
- `ip_range`: IP range
- `mobile_app`: Mobile application

**Example:**
```bash
curl -X POST http://localhost:5000/api/targets/1/scope \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "wildcard",
    "value": "*.example.com",
    "in_scope": true
  }'
```

**Response:** (201 Created)
```json
{
  "success": true,
  "data": {
    "id": 2,
    "target_id": 1,
    "scope_type": "wildcard",
    "value": "*.example.com",
    ...
  }
}
```

---

### Attack Profiles

#### GET /api/targets/{id}/attack-profiles

Get all attack profiles for a target.

**Example:**
```bash
curl http://localhost:5000/api/targets/1/attack-profiles
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "target_id": 1,
      "attack_type": "recon",
      "enabled": true,
      "rate_limit": 5,
      "max_threads": 5,
      "config_json": null,
      "notes": null,
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:00:00"
    }
  ]
}
```

#### PUT /api/targets/{id}/attack-profiles/{profile_id}

Update an attack profile.

**Request Body:**
```json
{
  "enabled": true,
  "rate_limit": 20,
  "max_threads": 10,
  "notes": "Increased rate limit"
}
```

**Attack Types:**
- `recon`: General reconnaissance
- `subdomain_enum`: Subdomain enumeration
- `port_scan`: Port scanning
- `directory_brute`: Directory bruteforcing
- `xss`: Cross-site scripting
- `sqli`: SQL injection
- `lfi`: Local file inclusion
- `rfi`: Remote file inclusion
- `ssrf`: Server-side request forgery
- `api_fuzzing`: API fuzzing
- `auth_bypass`: Authentication bypass
- `idor`: Insecure direct object reference
- `xxe`: XML external entity
- `deserialization`: Deserialization attacks
- `custom`: Custom attack type

**Example:**
```bash
curl -X PUT http://localhost:5000/api/targets/1/attack-profiles/1 \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "rate_limit": 20
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "enabled": true,
    "rate_limit": 20,
    ...
  }
}
```

---

### Scan Results

#### GET /api/results

Get scan results with optional filters.

**Query Parameters:**
- `target_id` (optional): Filter by target
- `attack_type` (optional): Filter by attack type
- `status` (optional): Filter by status
- `limit` (optional): Max results (default: 50)

**Example:**
```bash
curl http://localhost:5000/api/results
curl http://localhost:5000/api/results?target_id=1
curl http://localhost:5000/api/results?status=completed&limit=10
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "target_id": 1,
      "attack_type": "recon",
      "status": "completed",
      "severity": "info",
      "result_summary": "Found 10 subdomains",
      "requests_sent": 100,
      "vulnerabilities_found": 0,
      "duration_seconds": 120,
      "error_message": null,
      "created_at": "2024-01-15T10:00:00",
      "started_at": "2024-01-15T10:00:00",
      "completed_at": "2024-01-15T10:02:00"
    }
  ]
}
```

#### GET /api/results/{id}

Get a specific scan result.

**Example:**
```bash
curl http://localhost:5000/api/results/1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "target_id": 1,
    "attack_type": "recon",
    "status": "completed",
    ...
  }
}
```

**Status Values:**
- `pending`: Scan queued
- `running`: Scan in progress
- `completed`: Scan finished successfully
- `failed`: Scan failed
- `cancelled`: Scan was cancelled

**Severity Values:**
- `critical`: Critical vulnerability
- `high`: High severity
- `medium`: Medium severity
- `low`: Low severity
- `info`: Informational

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 500 | Internal Server Error |

## Rate Limiting (Future)

Rate limiting will be implemented in Phase 2+:
- 100 requests per hour per IP
- 1000 requests per hour for authenticated users

## Authentication (Future)

API authentication will be implemented in Phase 2+ using:
- JWT tokens
- API keys
- OAuth2 (optional)

---

**Last Updated**: Phase 1  
**API Version**: 1.0.0
