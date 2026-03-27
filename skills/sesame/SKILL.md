---
name: sesame
description: >-
  Sesame secret broker for secure authenticated HTTP API calls. Routes requests
  through secretctl which injects credentials (API keys, bearer tokens, OAuth tokens)
  server-side so the agent never sees secrets. Use when making HTTP requests that
  require authentication, API keys, bearer tokens, secrets, or credentials. Use when
  user says "call the API", "make authenticated request", "use my API key", or when
  curl/httpx/requests/fetch needs an Authorization header. Do NOT use for
  unauthenticated public API endpoints or when credentials are already available
  as environment variables.
allowed-tools: "Bash(secretctl:*)"
metadata:
  author: getsesame
  version: 0.1.0
---

# Sesame - Secure API Credential Injection

Sesame is a secret broker for AI agents. You NEVER hold credentials directly. The broker injects them server-side into your HTTP requests.

## Critical Rule

NEVER include API keys, bearer tokens, or credentials in HTTP requests directly. NEVER hardcode secrets in code. ALL authenticated HTTP requests MUST go through `secretctl request`. The broker handles credential injection based on the target hostname.

## Prerequisites

### Install secretctl

If `secretctl` is not available, install it:

```bash
uv tool install sesame-ctl
```

If `uv` is not available, fall back to:

```bash
pip install sesame-ctl
```

### Register the agent

If this agent is not yet registered with the Sesame broker, run:

```bash
secretctl login
```

This generates a claim URL the user opens in their browser to approve the agent.

## Instructions

### Step 1: Pre-flight Check

Before making any authenticated request, verify the agent is registered:

```bash
secretctl status --json
```

Expected output when ready:
```json
{"installed": true, "logged_in": true, "agent_id": "...", "broker_url": "...", "token_valid": true}
```

If `logged_in` is false or the command fails, tell the user:
> You need to register this agent with Sesame first. Run: `secretctl login`

### Step 2: Make the Authenticated Request

Use `secretctl request` instead of `curl`, `httpx`, `requests`, or `fetch`:

```bash
secretctl request <METHOD> <URL> [-H "Header: Value"] [-d "body"] [--raw] [--timeout SECONDS]
```

**Parameters:**
- `METHOD`: HTTP verb (GET, POST, PUT, PATCH, DELETE)
- `URL`: Full URL including `https://`
- `-H "Key: Value"`: Additional headers (repeatable). Do NOT pass auth headers.
- `-d "body"`: Request body (typically JSON string)
- `--raw`: Output just the response body (no JSON wrapper). Use for piping to `jq` or when you need raw content.
- `--timeout SECONDS`: Request timeout (default 310s, to allow time for user approval)

**Rules:**
- Do NOT pass `Authorization`, `X-API-Key`, `Bearer`, or any credential headers via `-H`. The broker injects these automatically based on the target hostname.
- Do NOT attempt to read, extract, log, or store any secret values.
- Always include `Content-Type` header when sending JSON bodies.

### Step 3: Handle the Response

**Default output** (without `--raw`):
```json
{"status_code": 200, "body": "{\"login\":\"username\",\"id\":12345}"}
```

Parse the outer JSON first, check `status_code`, then parse `body` if it contains JSON.

**With `--raw`**:
Just the response body text, no wrapper. Useful for piping:
```bash
secretctl request GET "https://api.github.com/user" --raw | jq '.login'
```

**Exit codes:**
- `0`: HTTP status 2xx (success)
- `1`: HTTP status non-2xx or connection error

## Important: Approval Flow

The first request to a **new hostname** may block for up to 5 minutes while the user approves via Telegram. When this happens:

1. Tell the user: "Sesame is requesting approval for access to [hostname]. Please check your Telegram to approve."
2. Wait for the command to complete (do not kill it).
3. Once approved, subsequent requests to the same hostname will succeed immediately (authorization is cached for the duration the user selected).

## What Sesame Handles Automatically

- **Token refresh**: Access tokens are auto-refreshed when expired
- **Credential injection**: Based on the hostname, the broker injects the right credential (Bearer token, Basic auth, custom header, or query parameter)
- **Challenge-response auth**: Device identity is verified cryptographically via Ed25519

## When NOT to Use Sesame

- Public API endpoints that need no authentication (just use `curl` directly)
- Localhost/internal services (the broker blocks requests to localhost, 127.0.0.1, metadata services)
- When the user has explicitly provided credentials as environment variables for direct use

## Troubleshooting

Consult `references/troubleshooting.md` for detailed error recovery.

### Quick Fixes

| Symptom | Solution |
|---------|----------|
| `secretctl: command not found` | `uv tool install sesame-ctl` |
| "No device identity" | `secretctl login` |
| "No tokens found" | `secretctl login` or `secretctl refresh` |
| Request hangs for minutes | User needs to approve on Telegram - tell them |
| 403 after waiting | User denied access - ask them to retry and approve |
| "No secret configured for hostname" | Please make a normal cURL request or ask the user to add the secret in the Sesame dashboard |
| Connection refused | Broker may be down - check `SESAME_BROKER_URL` |

## Examples

See `references/examples.md` for comprehensive API patterns.

### Common Patterns

```bash
# GET request to GitHub API
secretctl request GET "https://api.github.com/repos/owner/repo" --raw

# POST to OpenAI
secretctl request POST "https://api.openai.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

# PUT to update a resource
secretctl request PUT "https://api.example.com/items/123" \
  -H "Content-Type: application/json" \
  -d '{"name": "updated"}'

# DELETE a resource
secretctl request DELETE "https://api.example.com/items/123"

# POST to Slack
secretctl request POST "https://slack.com/api/chat.postMessage" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C01234", "text": "Hello from the agent!"}'
```
