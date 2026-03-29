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
  version: 0.3.0
---

# Sesame - Secure API Credential Injection

Sesame is a secret broker for AI agents. You NEVER hold credentials directly. The broker injects them server-side into your HTTP requests.

## Critical Rule

NEVER include API keys, bearer tokens, or credentials in HTTP requests directly. NEVER hardcode secrets in code. ALL authenticated HTTP requests MUST go through `secretctl request`. The broker handles credential injection based on the target hostname.

## Prerequisites

### Install secretctl

If `secretctl` is not available, install it:

```bash
curl -fsSL https://getsesame.dev/install.sh | sh
```

This downloads a standalone binary — no Python or pip required. Verify with:

```bash
secretctl --version
```

### Register the agent

If this agent is not yet registered with the Sesame broker, run:

```bash
secretctl login
```

There are two registration modes:

- **Mode B (default):** Agent-initiated. Generates a claim URL the user opens in their browser to approve the agent.
- **Mode A (dashboard-initiated):** User creates a registration link in the dashboard and passes it to the agent:
  ```bash
  secretctl login sesame-register:<token>
  ```
  Or with a bootstrap token directly:
  ```bash
  secretctl login --bootstrap-token <token>
  ```

The default broker is `https://getsesame.dev`. Override with `--broker-url` or the `SESAME_BROKER_URL` env var for self-hosted brokers.

If an agent is already registered on this device, `secretctl login` will warn and suggest `secretctl refresh` instead. To register an additional agent, use `--new`:

```bash
secretctl login --new
```

## Instructions

### Step 1: Pre-flight Check

Before making any authenticated request, verify the agent is registered:

```bash
secretctl status
```

Expected output when ready:
```
Device fingerprint: abc123...
Agents (1):
   * <agent-id>
Active: <agent-id>
Tokens: present
```

If no device identity exists or no agents are shown, tell the user:
> You need to register this agent with Sesame first. Run: `secretctl login`

### Step 2: Check Available Hostnames (REQUIRED)

Before making ANY authenticated HTTP request, ALWAYS check which hostnames have secrets configured:

```bash
secretctl hostnames
```

Or for machine-readable output:

```bash
secretctl hostnames --json
```

This returns hostnames like `api.github.com`, `api.openai.com`. **Only use `secretctl request` for hostnames in this list.** For any hostname NOT in this list, use a normal `curl` request instead or ask the user to add the secret in the Sesame dashboard.

This step prevents unnecessary Telegram approval prompts and failed requests.

### Step 3: Make the Authenticated Request

Use `secretctl request` instead of `curl`, `httpx`, `requests`, or `fetch`:

```bash
secretctl request <METHOD> <URL> [-H "Header: Value"] [-d "body"] [--raw]
```

**Parameters:**
- `METHOD`: HTTP verb (GET, POST, PUT, PATCH, DELETE)
- `URL`: Full URL including `https://`
- `-H "Key: Value"`: Additional headers (repeatable). Do NOT pass auth headers.
- `-d "body"`: Request body (typically JSON string)
- `--raw`: Output just the response body (no JSON wrapper). Use for piping to `jq` or when you need raw content.

**Rules:**
- Do NOT pass `Authorization`, `X-API-Key`, `Bearer`, or any credential headers via `-H`. The broker injects these automatically based on the target hostname.
- Do NOT attempt to read, extract, log, or store any secret values.
- Always include `Content-Type` header when sending JSON bodies.

### Step 4: Handle the Response

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

If the request is denied by policy (e.g., wrong HTTP method or restricted path), secretctl will print an "Access denied" message with details about the policy restriction. Ask the secret owner to update the policy in the Sesame dashboard.

## What Sesame Handles Automatically

- **Token refresh**: Access tokens are auto-refreshed when expired (challenge-response with Ed25519 device key)
- **Credential injection**: Based on the hostname, the broker injects the right credential (Bearer token, Basic auth, custom header, or query parameter)
- **Challenge-response auth**: Device identity is verified cryptographically via Ed25519
- **Policy enforcement**: Per-secret policies can restrict allowed methods, paths, and subdomains

## When NOT to Use Sesame

- Public API endpoints that need no authentication (just use `curl` directly)
- Localhost/internal services (the broker blocks requests to localhost, 127.0.0.1, metadata services)
- When the user has explicitly provided credentials as environment variables for direct use

## Troubleshooting

Consult `references/troubleshooting.md` for detailed error recovery.

### Quick Fixes

| Symptom | Solution |
|---------|----------|
| `secretctl: command not found` | `curl -fsSL https://getsesame.dev/install.sh \| sh` |
| "No device identity" | `secretctl login` |
| "No tokens found" | `secretctl login` or `secretctl refresh` |
| "You already have an active agent" | Use `secretctl refresh` or `secretctl login --new` |
| Request hangs for minutes | User needs to approve on Telegram - tell them |
| 403 after waiting | User denied access - ask them to retry and approve |
| "Access denied" with policy details | Policy restricts this request - ask owner to update in dashboard |
| "No secret configured for hostname" | Make a normal cURL request or ask user to add secret in dashboard |
| Connection refused | Broker may be down - check `secretctl status` |

## Examples

See `references/examples.md` for comprehensive API patterns.

### Common Patterns

```bash
# Always check available hostnames first
secretctl hostnames

# GET request to GitHub API
secretctl request GET "https://api.github.com/repos/owner/repo" --raw

# POST to OpenAI
secretctl request POST "https://api.openai.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

# POST to Anthropic
secretctl request POST "https://api.anthropic.com/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model": "claude-sonnet-4-20250514", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello"}]}'

# List Anthropic models
secretctl request GET "https://api.anthropic.com/v1/models" \
  -H "anthropic-version: 2023-06-01" --raw

# POST to Slack
secretctl request POST "https://slack.com/api/chat.postMessage" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C01234", "text": "Hello from the agent!"}'

# DELETE a resource
secretctl request DELETE "https://api.example.com/items/123"
```
