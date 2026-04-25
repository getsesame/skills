# Sesame Troubleshooting Guide

## Installation Issues

### `sesame: command not found`
The Sesame CLI is not installed or not on PATH.

**Solution:**
Ask the user to install `sesame` following Sesame's install instructions. Do not attempt to install it automatically — the skill never runs installers or shell downloads.

If installed but not found, ensure the install location is on the user's PATH (default: `/usr/local/bin` or `~/.local/bin`).

## Authentication Issues

### "No device identity"
No Ed25519 device keypair exists. This means the agent has never been registered.

**Solution:**
```bash
sesame login
```

This will generate a claim URL for the user to open in their browser to approve the agent. The broker URL is configured at `sesame` install time.

### "You already have an active agent"
An agent is already registered on this device.

**Solution:**
- To re-authenticate the existing agent: `sesame refresh`
- To register an additional agent: `sesame login --new`

### "No tokens found"
Device identity exists but no access/refresh tokens are stored.

**Solution:**
```bash
sesame refresh
```

If refresh fails:
```bash
sesame login --new
```

### "Could not obtain valid token"
Both token refresh and challenge-response auth failed.

**Possible causes:**
- Agent has been revoked by the user
- Broker is unreachable
- Device keys have been corrupted

**Solution:**
1. Check broker connectivity: `sesame status` (reports whether the broker is reachable)
2. Re-register: `sesame login --new`

## Request Issues

### Request hangs / takes a long time
The broker is waiting for the user to approve access to this hostname via Telegram. This is normal for first-time access to a new API.

**What to do:**
1. Tell the user to check their Telegram app
2. The approval message shows the hostname and offers duration options and policy presets (full access, read-only, custom)
3. Once approved, subsequent requests to the same hostname will be instant

### 403 "Access denied by user"
The user explicitly denied the access request on Telegram.

**Solution:**
1. Ask the user if they intended to deny access
2. If it was a mistake, retry the request - a new approval prompt will be sent
3. The user can also grant access proactively via the Sesame dashboard

### 403 "Access denied" with policy details
The request was blocked by the access policy set for this secret (e.g., wrong HTTP method, restricted path, disallowed subdomain).

**Solution:**
Ask the secret owner to update the policy in the Sesame dashboard. The error message includes the specific reason (method not allowed, path denied, etc.).

### 422 "No secret configured for hostname"
The broker has nothing mapped to the target hostname.

**Prevention:** Always run `sesame hostnames` before making requests to check which hostnames are available.

**Solution:**
Make a normal cURL request instead, or tell the user: "Nothing is configured in Sesame for [hostname]. Please add it in the Sesame dashboard:
1. Go to the Sesame web dashboard
2. Add a new entry for the hostname [hostname]
3. Set the attachment mode (Bearer, Basic, Header, or Query)
4. Store the token value"

### Connection errors / timeouts
The broker server is unreachable.

**Checklist:**
1. Check broker health + agent status: `sesame status`
2. Check network connectivity
3. Confirm the configured broker URL with the user

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
sesame status

# Switch to the correct agent
sesame switch <agent-id>

# Or pin for this shell session
export SESAME_AGENT_ID=<agent-id>
```
