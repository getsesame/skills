# Sesame Troubleshooting Guide

## Installation Issues

### `secretctl: command not found`
The Sesame CLI is not installed or not on PATH.

**Solution:**
```bash
uv tool install sesame-ctl
# or
pip install sesame-ctl
```

If installed but not found, check that the Python scripts directory is on your PATH.

## Authentication Issues

### "No device identity"
No Ed25519 device keypair exists. This means the agent has never been registered.

**Solution:**
```bash
secretctl login
```

This will generate a claim URL for the user to open in their browser to approve the agent.

### "No tokens found"
Device identity exists but no access/refresh tokens are stored.

**Solution:**
```bash
secretctl refresh
```

If refresh fails:
```bash
secretctl login --new
```

### "Could not obtain valid token"
Both token refresh and challenge-response auth failed.

**Possible causes:**
- Agent has been revoked by the user
- Broker is unreachable
- Device keys have been corrupted

**Solution:**
1. Check broker connectivity: `curl -s $SESAME_BROKER_URL/health`
2. Re-register: `secretctl login --new`

## Request Issues

### Request hangs / takes a long time
The broker is waiting for the user to approve access to this hostname via Telegram. This is normal for first-time access to a new API.

**What to do:**
1. Tell the user to check their Telegram app
2. The approval message shows the hostname and offers duration options (1h, 4h, 8h, 24h)
3. Once approved, subsequent requests to the same hostname will be instant

### 403 "Access denied by user"
The user explicitly denied the access request on Telegram.

**Solution:**
1. Ask the user if they intended to deny access
2. If it was a mistake, retry the request - a new approval prompt will be sent
3. The user can also grant access proactively via the Sesame dashboard

### 422 "No secret configured for hostname"
The broker has no secret mapped to the target hostname.

**Solution:**
Make a normal cURL request instead, or tell the user: "No secret is configured in Sesame for [hostname]. Please add it in the Sesame dashboard:
1. Go to the Sesame web dashboard
2. Add a new secret with the hostname [hostname]
3. Set the injection mode (Bearer, Basic, Header, or Query)
4. Store the credential value"

### Connection errors / timeouts
The broker server is unreachable.

**Checklist:**
1. Check `SESAME_BROKER_URL` environment variable
2. Verify broker is running: `curl -s $SESAME_BROKER_URL/health`
3. Check network connectivity

### HTTP error responses (4xx, 5xx)
These are responses from the upstream API, proxied through Sesame.

**Reading the response:**
- `status_code` is from the upstream API, not Sesame
- `body` contains the upstream API's error message
- Parse the body for API-specific error details

## Multi-Agent Issues

### Wrong agent is active
If multiple agents are registered on this device, the wrong one may be active.

**Solution:**
```bash
# Check which agent is active
secretctl status

# Switch to the correct agent
secretctl switch <agent-id>

# Or pin for this shell session
export SESAME_AGENT_ID=<agent-id>
```
