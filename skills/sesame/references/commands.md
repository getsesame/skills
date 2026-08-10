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

## Transparent egress (wrap unmodified agents)

```bash
sesame launch -- python agent.py        # run any command with brokered egress transparently mediated
sesame init                             # print the proxy/CA env exports (headless/CI)
sesame onboard hermes --dry-run         # read-only plan: detected Hermes surfaces, owners, restart preview
sesame onboard hermes                   # restart safe targets through Sesame; installs OS trust; ends with doctor
sesame onboard hermes --verify-only     # recheck an installed setup without changing anything
sesame onboard hermes --rollback <id>   # restore one target's original launch configuration
sesame trust                            # install the tenant root into the OS trust store (once per machine)
sesame trust --uninstall                # reverse it
sesame doctor --json                    # per-runtime trust verification; exit 1 on any failure
sesame proxyd install                   # download the edge proxy binary
sesame egress uninstall --dry-run       # preview reversible machine-wide egress removal
```

## Proxy keys

Scoped access policies are viewed and edited in the Sesame dashboard, not the CLI.

```bash
sesame proxy-key create                 # mint an edge-proxy bearer credential
sesame proxy-key list
sesame proxy-key revoke <prefix>
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
sesame deploy status                              # CloudFormation stack + broker health + running version
sesame deploy update                              # converge the box: install/enable the auto-updater, pull, recreate
sesame deploy update --image-tag v0.3.70          # pin a specific version — PAUSES auto-update so the pin sticks
sesame deploy restart                             # restart the broker container
sesame deploy logs                                # tail broker logs
sesame deploy destroy                             # tear down the stack
```

Self-hosted brokers auto-update: an updater sidecar on each box follows the
`ghcr.io/getsesame/sesame:stable` channel (~30 min poll), so `deploy update`
is only needed to enable it on older boxes or for emergency pins. A plain
`deploy update` re-enables auto-update after a pin
(`SESAME_AUTO_UPDATE=false` in the box `.env` is the pause flag).

## CLI self-update

```bash
sesame update            # update the CLI to the latest release now
sesame update --check    # report whether an update exists, don't install
```

The CLI also updates itself automatically: each invocation does a throttled
(30-min) check and, when a newer release exists, runs the installer in the
background — the invoked command is never delayed; a one-line notice goes to
stderr. Opt out with `SESAME_CLI_AUTO_UPDATE=false` in the environment.
Auto-update never runs from source checkouts or when `CI` is set.

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
