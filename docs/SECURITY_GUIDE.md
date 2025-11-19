# FlowRAG Security Guide

## Overview

This guide explains the security features implemented in FlowRAG and how to configure them for different environments.

**Key Principle**: All security features are **opt-in** and **backward compatible**. The system defaults to development mode with security features disabled, ensuring existing functionality continues to work unchanged.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Configuration](#configuration)
3. [Security Features](#security-features)
4. [Production Deployment](#production-deployment)
5. [Development Workflow](#development-workflow)
6. [Testing Security](#testing-security)
7. [Troubleshooting](#troubleshooting)

---

## Security Architecture

FlowRAG implements multiple layers of security:

```
┌─────────────────────────────────────────┐
│         Client Application              │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Layer 1: CORS Validation               │
│  - Origin whitelisting                  │
│  - Method/header restrictions           │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Layer 2: Rate Limiting (Optional)      │
│  - Request throttling                   │
│  - Per-IP limits                        │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Layer 3: Authentication (Optional)     │
│  - API Key validation                   │
│  - X-API-Key header                     │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Layer 4: Input Validation              │
│  - Schema validation                    │
│  - Length limits                        │
│  - Format checks                        │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Layer 5: Path Validation (Optional)    │
│  - Directory traversal prevention       │
│  - Path whitelisting                    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│        Business Logic                   │
└─────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

All security settings are configured via environment variables in `.env`:

```bash
# Security Controls
ENABLE_SECURITY=false              # API key authentication
ENABLE_RATE_LIMITING=false         # Request rate limiting
ENABLE_PATH_VALIDATION=true        # Path traversal prevention

# API Keys (comma-separated)
API_KEYS=key1-abc123,key2-def456

# Path Validation
ALLOWED_DIRECTORIES=/app/data,/app/uploads

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# CORS Origins (comma-separated)
CORS_ORIGINS=https://myapp.com,https://www.myapp.com

# File Size Limits
MAX_FILE_SIZE_MB=10
```

### Development vs Production Defaults

| Feature              | Development Default | Production Default |
|---------------------|--------------------|--------------------|
| API Authentication   | **Disabled**       | Configurable       |
| Rate Limiting        | **Disabled**       | Configurable       |
| Path Validation      | **Enabled**        | **Enabled**        |
| CORS                 | Localhost only     | Explicit whitelist |
| Debug Logging        | Enabled            | Disabled           |

---

## Security Features

### 1. API Key Authentication

**Purpose**: Prevent unauthorized access to API endpoints.

**How it works**:
- Requires `X-API-Key` header in all requests
- Validates against configured API keys
- Returns 401 Unauthorized if missing, 403 Forbidden if invalid

**Enabling**:
```bash
# .env
ENABLE_SECURITY=true
API_KEYS=your-secret-key-1,your-secret-key-2
```

**Generating API Keys**:
```bash
# Generate a secure random key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Client Usage**:
```python
import requests

headers = {"X-API-Key": "your-api-key-here"}
response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={"query": "What is this code?", "namespace": "myproject"},
    headers=headers
)
```

```bash
# cURL example
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this code?", "namespace": "myproject"}'
```

---

### 2. Rate Limiting

**Purpose**: Prevent abuse and DoS attacks.

**How it works**:
- Limits requests per IP address
- Uses slowapi library with in-memory storage
- Returns 429 Too Many Requests when limit exceeded

**Enabling**:
```bash
# .env
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60  # 60 requests per minute per IP
```

**Production Note**: For distributed systems, consider using Redis for rate limit storage:
```python
# In api/security/rate_limit.py
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",  # Use Redis instead of memory
)
```

---

### 3. Path Validation

**Purpose**: Prevent directory traversal attacks.

**How it works**:
- Validates all file paths in requests
- Checks against whitelist of allowed directories
- Blocks `..`, null bytes, and suspicious patterns

**Configuration**:
```bash
# .env
ENABLE_PATH_VALIDATION=true
ALLOWED_DIRECTORIES=/app/data,/app/uploads,/tmp/flowrag
```

**Default Behavior** (when ALLOWED_DIRECTORIES is empty):
- Development: Allows current directory and user home directory
- Production: Requires explicit configuration

**Example**:
```python
# ✅ Allowed: /app/data/project/file.py
# ❌ Blocked: /app/data/../../../etc/passwd
# ❌ Blocked: /app/data/project/../../sensitive.txt
```

---

### 4. Input Validation

**Purpose**: Prevent injection attacks and malformed input.

**Implemented via Pydantic schemas**:

```python
class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    namespace: str = Field(min_length=1, max_length=255)

    @field_validator("query")
    def validate_query(cls, v: str) -> str:
        # Check for null bytes
        if "\x00" in v:
            raise ValueError("Invalid characters in query")
        return v.strip()

    @field_validator("namespace")
    def validate_namespace(cls, v: str) -> str:
        # Alphanumeric, underscore, hyphen, period only
        if not all(c.isalnum() or c in ('_', '-', '.') for c in v):
            raise ValueError("Invalid namespace format")
        # Prevent directory traversal
        if ".." in v:
            raise ValueError("Invalid namespace format")
        return v.strip()
```

**Validations Applied**:
- Length limits (prevent DoS)
- Format validation (alphanumeric, specific patterns)
- Null byte detection
- Directory traversal prevention
- Type enforcement

---

### 5. CORS Configuration

**Purpose**: Control which web origins can access the API.

**Development**:
```python
# Automatically allows:
# - http://localhost:3000, :5173, :8080, :8501
# - http://127.0.0.1:3000, :5173, :8080, :8501
```

**Production**:
```bash
# .env
ENV=production
CORS_ORIGINS=https://myapp.com,https://www.myapp.com,https://app.example.org
```

**Restrictions by Environment**:

| Environment | Allowed Methods | Allowed Headers |
|------------|----------------|----------------|
| Development | All (`*`) | All (`*`) |
| Production | GET, POST, PUT, DELETE | Content-Type, Authorization, X-API-Key, Accept, Origin |

---

## Production Deployment

### Step-by-Step Production Setup

#### 1. Generate API Keys
```bash
# Generate strong API keys
python3 -c "import secrets; [print(secrets.token_urlsafe(32)) for _ in range(3)]"
```

#### 2. Configure .env
```bash
# Application
ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# Security
ENABLE_SECURITY=true
ENABLE_RATE_LIMITING=true
ENABLE_PATH_VALIDATION=true

# API Keys (use generated keys from step 1)
API_KEYS=prod-key-xyz123abc,prod-key-def456ghi

# Paths
ALLOWED_DIRECTORIES=/app/data,/app/uploads

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30

# File Limits
MAX_FILE_SIZE_MB=50

# Secrets
SECRET_KEY=<generate-64-character-random-string>
```

#### 3. Rotate Exposed Keys
```bash
# If keys were exposed in git history
# Generate new OpenAI key: https://platform.openai.com/api-keys
# Generate new Anthropic key: https://console.anthropic.com/settings/keys
OPENAI_API_KEY=sk-proj-NEW-KEY-HERE
ANTHROPIC_API_KEY=sk-ant-api03-NEW-KEY-HERE
```

#### 4. Update Nginx/Reverse Proxy
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Reverse Proxy to FlowRAG
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Rate Limiting at Nginx Level (additional protection)
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

#### 5. Test Security
```bash
# Test without API key (should fail)
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "namespace": "test"}'
# Expected: 401 Unauthorized

# Test with valid API key (should succeed)
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "X-API-Key: your-production-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "namespace": "test"}'
# Expected: 200 OK

# Test path traversal (should fail)
curl -X POST https://api.yourdomain.com/api/v1/ingest/file \
  -H "X-API-Key: your-production-key" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/etc/passwd", "namespace": "test"}'
# Expected: 400 Bad Request or 403 Forbidden

# Test rate limiting
for i in {1..100}; do
  curl -X GET https://api.yourdomain.com/api/v1/health
done
# Expected: 429 Too Many Requests after limit exceeded
```

---

## Development Workflow

### Running with Security Disabled (Default)

```bash
# .env
ENV=development
DEBUG=true
ENABLE_SECURITY=false
ENABLE_RATE_LIMITING=false
ENABLE_PATH_VALIDATION=true  # Still recommended

# Start server
cd /path/to/flowrag-master
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# No API key needed
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "namespace": "test"}'
```

### Testing with Security Enabled Locally

```bash
# .env
ENABLE_SECURITY=true
API_KEYS=dev-test-key-123

# Test with key
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: dev-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "namespace": "test"}'
```

---

## Testing Security

### Security Test Checklist

- [ ] **Authentication**: Requests without API key are rejected (when enabled)
- [ ] **Path Traversal**: Attempts to access `../` paths are blocked
- [ ] **Rate Limiting**: Excessive requests return 429 (when enabled)
- [ ] **CORS**: Only whitelisted origins can access API
- [ ] **Input Validation**: Oversized or malformed inputs are rejected
- [ ] **Null Bytes**: Inputs with `\x00` are rejected
- [ ] **Namespace Validation**: Invalid characters/formats are rejected
- [ ] **File Size**: Files exceeding limit are rejected

### Automated Security Tests

Create `tests/security/test_security_features.py`:

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api_key_required():
    """Test that API key is required when security enabled."""
    # Assuming ENABLE_SECURITY=true
    response = client.post(
        "/api/v1/query",
        json={"query": "test", "namespace": "test"}
    )
    assert response.status_code == 401

def test_path_traversal_blocked():
    """Test that path traversal is blocked."""
    response = client.post(
        "/api/v1/ingest/file",
        json={
            "file_path": "../../../etc/passwd",
            "namespace": "test"
        },
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code in [400, 403]

def test_rate_limiting():
    """Test that rate limiting works."""
    # Make 100 requests rapidly
    for i in range(100):
        response = client.get("/api/v1/health")
    # Should eventually get rate limited
    assert response.status_code == 429
```

---

## Troubleshooting

### Common Issues

#### 1. "API key is required" error

**Symptom**: All requests return 401 Unauthorized

**Cause**: Security is enabled but no API key provided

**Solutions**:
```bash
# Option A: Disable security for development
ENABLE_SECURITY=false

# Option B: Provide API key in requests
curl -H "X-API-Key: your-key" ...
```

---

#### 2. "Access denied: Path outside allowed directories"

**Symptom**: File ingestion fails with 403 Forbidden

**Cause**: Path validation is blocking the file path

**Solutions**:
```bash
# Option A: Add directory to whitelist
ALLOWED_DIRECTORIES=/your/project/path,/another/path

# Option B: Disable path validation (NOT recommended for production)
ENABLE_PATH_VALIDATION=false

# Option C: Use absolute path within allowed directory
# Instead of: ./myfile.py
# Use: /full/path/to/myfile.py
```

---

#### 3. "429 Too Many Requests"

**Symptom**: Requests fail after several attempts

**Cause**: Rate limit exceeded

**Solutions**:
```bash
# Option A: Wait 1 minute for limit to reset

# Option B: Increase rate limit
RATE_LIMIT_PER_MINUTE=120

# Option C: Disable rate limiting for development
ENABLE_RATE_LIMITING=false
```

---

#### 4. CORS errors in browser

**Symptom**: Browser console shows CORS policy error

**Cause**: Frontend origin not whitelisted

**Solutions**:
```bash
# Development: Ensure running in development mode
ENV=development
DEBUG=true

# Production: Add origin to whitelist
CORS_ORIGINS=https://your-frontend-domain.com
```

---

#### 5. "Invalid namespace format"

**Symptom**: Requests fail with 400 Bad Request on namespace validation

**Cause**: Namespace contains invalid characters or patterns

**Solutions**:
```python
# ✅ Valid namespaces:
"my_project"
"project-v2"
"test.namespace"
"MyProject123"

# ❌ Invalid namespaces:
"my project"  # No spaces
"../etc"      # No directory traversal
".hidden"     # Cannot start with .
"project."    # Cannot end with .
"pro@ject"    # Only alphanumeric, _, -, . allowed
```

---

### Debug Logging

Enable debug logging to troubleshoot security issues:

```bash
# .env
LOG_LEVEL=DEBUG

# Check logs
tail -f logs/flowrag.log | grep -i security
```

Look for messages like:
```
🔓 Security is DISABLED - All API endpoints are open!
🔓 Rate limiting is DISABLED - API can be abused!
✅ Rate limiting enabled: 60/minute
✅ CORS: Production mode - 2 origins whitelisted
```

---

## Security Best Practices

1. **Never commit .env files** to version control
2. **Rotate API keys** regularly (every 90 days)
3. **Use HTTPS** in production (via reverse proxy)
4. **Enable all security features** in production
5. **Monitor logs** for suspicious activity
6. **Keep dependencies updated** (`pip install --upgrade`)
7. **Use environment-specific configurations** (dev vs prod)
8. **Implement audit logging** for sensitive operations
9. **Regular security audits** (use tools like `bandit`, `safety`)
10. **Principle of least privilege** (minimal file system access)

---

## Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/concepts/validators/)
- [SlowAPI Rate Limiting](https://slowapi.readthedocs.io/)

---

## Support

For security-related questions or to report vulnerabilities:

1. Check this guide and `docs/SECURITY_AUDIT.md`
2. Review `.env.example` for configuration options
3. Enable debug logging for troubleshooting
4. File an issue on GitHub (for non-sensitive issues)
5. Contact security team directly (for vulnerabilities)

---

**Last Updated**: 2025-11-10
**Version**: 1.0.0
