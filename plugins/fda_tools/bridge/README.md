# FDA Tools Bridge Server

HTTP REST API bridge between OpenClaw TypeScript skill and FDA Tools Python plugin.

## Quick Start

### Install Dependencies

```bash
pip3 install --break-system-packages -r requirements.txt
```

### Run Server

```bash
python3 server.py
```

Server will start at: `http://127.0.0.1:18790`

### Test Server

```bash
curl http://localhost:18790/health
```

## API Endpoints

### GET /health
Health check with system status

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 42,
  "sessions_active": 0,
  "commands_available": 68
}
```

### GET /commands
List available FDA commands

**Response:**
```json
{
  "commands": [
    {
      "name": "research",
      "description": "Research predicate devices...",
      "args": "--product-code <code>",
      "allowed_tools": "Read,Write,Bash,Grep"
    }
  ],
  "total": 68
}
```

### POST /execute
Execute FDA command

**Request:**
```json
{
  "command": "research",
  "args": "--product-code DQY",
  "user_id": "user-123",
  "channel": "file"
}
```

**Response:**
```json
{
  "success": true,
  "result": "Command output...",
  "classification": "PUBLIC",
  "llm_provider": "none",
  "session_id": "abc123",
  "duration_ms": 1234
}
```

### POST /session
Create or retrieve session

**Request:**
```json
{
  "user_id": "user-123",
  "session_id": "existing-session-id"  // Optional
}
```

### GET /session/{session_id}
Get session details

### GET /sessions?user_id=user-123
List sessions (optionally filtered by user)

### GET /tools
List available tool emulators

### GET /audit/integrity
Verify audit log integrity

## Architecture

```
OpenClaw Skill (TypeScript)
         ↓
    HTTP Bridge Server (Python/FastAPI)
         ↓
    FDA Tools Plugin (Python)
```

## Configuration

Edit `server.py` to change:

- **Host:** `SERVER_HOST = "127.0.0.1"`
- **Port:** `SERVER_PORT = 18790`
- **Version:** `SERVER_VERSION = "1.0.0"`

## Security

- Server binds to localhost only (127.0.0.1)
- CORS enabled for localhost origins
- Session management with in-memory storage
- Audit logging for all command executions

For production:
- Add API key authentication
- Implement rate limiting
- Use persistent session storage (Redis/database)
- Enable HTTPS with reverse proxy

## Development

### Add New Endpoint

1. Define Pydantic models for request/response
2. Create endpoint handler with @app decorator
3. Add audit logging
4. Update TypeScript types in `openclaw-skill/bridge/types.ts`

### Debugging

Enable debug logging:

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Files

- `server.py` - Main FastAPI application
- `requirements.txt` - Python dependencies
- `__init__.py` - Package initialization

## Dependencies

- fastapi==0.109.0 - Web framework
- uvicorn[standard]==0.27.0 - ASGI server
- pydantic==2.6.0 - Data validation

## License

MIT
