# Quick Start: OpenClaw Bridge Server

Fast setup guide for the FDA Tools OpenClaw skill and bridge server.

## Prerequisites Check

```bash
# Verify versions
node --version   # Need >= 18.0.0
python3 --version # Need >= 3.9
```

## Installation (2 minutes)

### 1. Build TypeScript Skill

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/openclaw-skill/
npm install
npm run build
```

**Expected output:** `dist/` directory created

### 2. Install Bridge Server

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/
pip3 install --break-system-packages -r requirements.txt
```

**Expected:** fastapi, uvicorn, pydantic installed

## Running (30 seconds)

### Start Bridge Server

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/
python3 server.py
```

**Expected output:**
```
======================================================================
FDA Tools Bridge Server v1.0.0
======================================================================
Server URL: http://127.0.0.1:18790
Commands available: 70
Server is ready to accept connections.
======================================================================
```

**Keep this terminal open** - server is now running

### Test Connection

Open new terminal:

```bash
curl http://localhost:18790/health
```

**Expected:** JSON response with `"status": "healthy"`

## Quick Tests

### List Available Commands

```bash
curl http://localhost:18790/commands | python3 -m json.tool | head -20
```

### Execute Test Command

```bash
curl -X POST http://localhost:18790/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "research",
    "args": "--product-code DQY",
    "user_id": "test-user",
    "channel": "file"
  }' | python3 -m json.tool
```

### Check Tools

```bash
curl http://localhost:18790/tools
```

## Verification

Run integration tests:

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/openclaw-skill/
npm test
```

**Expected:** 81/84 tests pass (96%)

## File Locations

```
Bridge Server:
  /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/server.py

TypeScript Skill:
  /home/linux/.claude/plugins/marketplaces/fda-tools/openclaw-skill/dist/index.js

Documentation:
  /home/linux/.claude/plugins/marketplaces/fda-tools/openclaw-skill/DEPLOYMENT.md
  /home/linux/.claude/plugins/marketplaces/fda-tools/FDA-26-IMPLEMENTATION-COMPLETE.md
```

## Troubleshooting

**Port 18790 in use:**
```bash
lsof -i :18790
kill -9 <PID>
```

**Missing Python packages:**
```bash
pip3 install --break-system-packages fastapi uvicorn pydantic
```

**TypeScript build fails:**
```bash
cd openclaw-skill/
rm -rf node_modules/
npm install
npm run build
```

## Next Steps

1. Review full documentation: `DEPLOYMENT.md`
2. Read implementation details: `FDA-26-IMPLEMENTATION-COMPLETE.md`
3. Configure OpenClaw to load the skill
4. Set up production deployment (systemd service)

## Status: ✅ Ready to Use

Bridge server is operational and ready for OpenClaw integration.
