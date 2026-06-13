# sesame CLI — command reference

One concise example per command. Run `sesame <command> --help` for the full
flag list; this file is the curated map. All commands operate on the broker
configured at `sesame login`; secret *values* are never passed on the CLI.

## Requests

```bash
# Proxy an authenticated request (broker attaches auth by hostname).
sesame request GET "https://api.github.com/user" --raw
sesame request POST "https://api.stripe.com/v1/charges" -H "Content-Type: application/x-www-form-urlencoded" -d "amount=500&currency=usd"
```

## Identity & session

```bash
sesame status                                   # device fingerprint, agents, token state
sesame login --broker-url https://my-broker.example   # register this agent (first run)
sesame login --new                              # register an additional agent on this device
sesame refresh                                  # mint fresh tokens for the active agent
sesame switch <agent-id>                        # make a different registered agent active
sesame police                                   # audit this machine for plaintext secrets an agent could read (read-only)
sesame help                                     # full top-level command list
```

## Hostnames

```bash
sesame hostnames            # hostnames that have a secret configured (use these with request)
sesame hostnames --json
```

## Secrets (draft flow — values are pasted in the dashboard, never the CLI)

`sesame secret create` returns a 15-minute dashboard link; the user opens it
and pastes the value. The CLI cannot read, set, or delete a live secret value.

```bash
# Create a draft + dashboard link. --mode: bearer | basic | header | query | webhook
sesame secret create "Stripe API" --hostname api.stripe.com --mode bearer
sesame secret create "Custom Key" --hostname api.example.com --mode header --header-name "X-API-Key"

# Prefill a default access policy at creation (see "Policy JSON" below)
sesame secret create "GitHub" --hostname api.github.com --policy-json '{"allowed_methods":["GET"]}'

# Point at a value already in the user's own AWS Secrets Manager (BYOK; no value pasted)
sesame secret create "Prod DB" --hostname db.example.com --aws-secret-arn arn:aws:secretsmanager:us-east-1:123:secret:prod-XYZ
```

### Secret drafts (manage pending drafts)

```bash
sesame secret draft list                                    # pending drafts owned by this user
sesame secret draft update <draft-id> --policy-json '{"allowed_methods":["GET"]}'  # e.g. restrict to GET
sesame secret draft update <draft-id> --clear-policy        # back to full access
sesame secret draft link <draft-id>                         # rotate a fresh 15-min dashboard link
sesame secret draft delete <draft-id>
```

## Agents

```bash
sesame agents list                      # agents registered with the broker
sesame agents deregister <agent-id>     # revoke an agent (kills sessions + refresh chain)
```

## Deploy (self-host on AWS)

```bash
sesame deploy aws --admin-email you@example.com   # provision broker in your AWS account
sesame deploy status                              # CloudFormation stack + broker health
sesame deploy update --image-tag main-abc1234     # pull a new image; migrations apply on broker start
sesame deploy restart                             # restart the broker container
sesame deploy logs                                # tail broker logs
sesame deploy destroy                             # tear down the stack
```

## Policy JSON

`--policy-json` / `--policy-file` (on `secret create` and `secret draft update`)
take a JSON object with these optional fields. Omit a field to leave that
dimension unrestricted; `{}` (or `--clear-policy`) means full access. **Unknown
keys are rejected (422)** — a typo will not silently widen access.

| Field | Type | Meaning |
|-------|------|---------|
| `allowed_methods` | `string[]` | HTTP methods allowed (e.g. `["GET","POST"]`) |
| `allowed_paths` | `string[]` | Glob path allowlist (e.g. `["/v1/**"]`) |
| `denied_paths` | `string[]` | Glob path denylist |
| `allowed_subdomains` | `string[]` | Subdomains allowed under the hostname |
| `path_rules` | `{path, methods}[]` | Per-path method limits; takes precedence over `allowed_methods`/`allowed_paths` |

```jsonc
// Read-only: GET only, anywhere on the host
{"allowed_methods": ["GET"]}

// Scope to a path subtree and a method set
{"allowed_methods": ["GET","POST"], "allowed_paths": ["/v1/**"]}

// Per-path rules (read everywhere, write only under /v1/issues)
{"path_rules": [
  {"path": "/**", "methods": ["GET"]},
  {"path": "/v1/issues/**", "methods": ["GET","POST"]}
]}
```
