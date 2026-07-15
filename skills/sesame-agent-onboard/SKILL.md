---
name: sesame-agent-onboard
description: >-
  Onboard an EXISTING agent (Hermes, OpenClaw, Claude Code, or any process that
  calls a provider API) to run KEYLESS behind Sesame via transparent egress. Use
  when the user says "onboard my agent to Sesame", "make my agent keyless", "set
  up Sesame on this box", "wrap my agent behind Sesame", or "route my agent's API
  calls through Sesame". This is the transparent `sesame launch` path (wrap the
  process + broker its hostnames) — NOT the cooperative `sesame request` path
  (that's the `sesame` skill), and NOT self-host broker deployment (that's the
  `sesame-onboard` skill). The agent runs the steps itself, driven by
  `sesame onboard detect`, pausing only at the human gates.
allowed-tools: "Bash(sesame:*), Bash(systemctl:*)"
metadata:
  author: sesame
  version: 0.1.0
---

# Sesame — Onboard an Agent to Keyless Transparent Egress

Goal: take an agent that today holds a real API credential and make it **keyless**
— the agent keeps working, but the real credential lives only in Sesame, injected
server-side per request with approval + audit. You (the assistant) run the CLI
steps; the CLI figures out the environment for you. Stop and ask the human only at
the three gates called out below.

## The one rule: detect first, never guess

**Always start with the read-only `detect`. Never mutate anything before you have
detected the environment.** Do not assume the deployment shape, the hostnames, or
whether a credential is present — `sesame onboard detect` tells you all of it, and
hand-guessing (e.g. brokering `api.openai.com` when the agent actually calls
`chatgpt.com`) is the #1 way this goes wrong.

```bash
sesame onboard detect --json
```

Read the JSON. The fields you drive off:

- `seat` — `in-container` | `vps-host` | `bare` | `unknown`
- `mechanism` — `container-entrypoint` | `systemd-system` | `systemd-user` | `launchd` | `bare-process` | `unknown`
- `product_hint` — best-effort agent name (label only; never gate on it)
- `egress.targets[]` — each `{host, provider, auth_kind, agent_holds_cred, brokered}`
  — **this is the ground truth for which hostnames to broker** (host ≠ brand name)
- `next[]` — an ordered checklist of step ids to execute (see the table below)

If `seat`/`mechanism` are `unknown` (detect emits `manual-review`), do NOT force a
guess — the `egress` section may still be populated (use it), and otherwise ask the
human how the agent is started. Report what detect *did* find rather than stalling.

## Prerequisites (do these if detect shows them missing)

`detect.evidence.sesame_installed` / `proxyd_installed` / `identity_present` tell you
what's already set up. If `next[]` contains these, handle them first:

- `install-proxyd` → `sesame proxyd install`
- `login` → `sesame login` — **HUMAN GATE #1 (device approval)**. The CLI prints a
  claim URL and waits. Tell the human immediately:
  > Open this URL while signed in to the Sesame dashboard and approve this device: `<claim URL>`
  Do not kill the command; it completes when they approve.

## Execute `next[]` in order

Map each step id from `detect.next` (and re-`detect` after big changes):

| Step id | What you run |
|---|---|
| `install-proxyd` | `sesame proxyd install` |
| `login` | `sesame login` → **HUMAN GATE #1** |
| `install-wrapper` | wrap per `mechanism` — see **Step A** below |
| `broker-host:<host>:<auth>` | broker that host — see **Step B** (**HUMAN GATE #2**) |
| `neutralize:<provider>` | go keyless — see **Step E** (only after verify is PROTECTED) |
| `verify` | `sesame onboard verify` — the gate, see **Step D** |

### Step A — Wrap the agent (from `mechanism`)

Pick the command by `mechanism` (the launch target is in `detect.evidence.launch_exec`
/ `entrypoint_path` / the systemd unit name):

- `container-entrypoint` → `sesame launch --install-wrapper <entrypoint_path>`
  (usually `/entrypoint.sh`)
- `systemd-user` → `sesame launch --install-wrapper <unit>.service --unit --user`
- `systemd-system` → `sesame launch --install-wrapper <unit>.service --unit`
- `launchd` (macOS) → `sesame launch --install-wrapper <label> --launchd`
  (the value is the launchd label from detect, e.g. `com.nousresearch.hermes`,
  or a plist path; it rewrites the plist's ProgramArguments in place, backup
  kept). A `/Library/LaunchDaemons` plist needs sudo; `~/Library/LaunchAgents`
  doesn't.
- `bare-process` (no supervisor) → there's nothing persistent to rewrite. Tell the
  human: either run the agent as `sesame launch -- <their command>`, or (better, so
  it survives reboot) create a systemd unit / launchd LaunchAgent and wrap that.
  Don't fabricate a unit.

The wrapper commands print the exact command to apply the change — `systemctl
restart …` for units, `launchctl unload … && launchctl load …` for plists.
**Applying it bounces the agent**, so confirm with the human before running it (a
`--user` unit restart needs no sudo; a system unit or LaunchDaemon does). Reverting
is always `sesame launch --revert-wrapper <same args>`.

### Step B — Broker each egress host — HUMAN GATE #2 (secret value)

For every `broker-host:<host>:<auth>` in `next` (equivalently, each
`egress.targets[]` with `brokered != true`): the human must add that secret — **the
CLI never accepts a secret value; it's always pasted in the dashboard.**

- `auth == api_key` → they add the secret at the getsesame.dev dashboard for
  `<host>`, matching the injection mode (Bearer for OpenAI/OpenRouter; the provider's
  API-key header — e.g. `x-api-key` — for Anthropic).
- `auth == oauth` → it's an OAuth **subscription** whose token rotates, so a static
  value goes stale. Start an OAuth2 secret from the CLI, then have them paste **only
  the refresh token** in the link it prints:

  ```bash
  sesame secret create <name> --hostname <host> --mode bearer \
    --oauth-token-url <provider-token-url> --oauth-client-id <client-id> \
    --oauth-grant refresh_token
  ```
  (For ChatGPT Codex: `--hostname chatgpt.com --oauth-token-url https://auth.openai.com/oauth/token`.)

Tell the human exactly which host + mode to add, and wait. When the secret is in
(`sesame hostnames` shows it), refresh the proxy so it's brokered immediately:

```bash
sesame proxyd reload
```

Without this, the proxy keeps splicing the new host for up to ~60s and calls leak.

### Step D — Verify (the gate)

```bash
sesame onboard verify
```

Exit `0` = **PROTECTED** (wrap + proxyd + identity + token + broker all pass). Exit
`1` = ran but not protected — read the failing checks it prints and fix them (wrong
wrap, proxyd not running, secret missing) before continuing. Exit `2` = couldn't
run. **Do not proceed to neutralize unless verify is PROTECTED.**

Optional before neutralize — exercise one real call so the human hits **HUMAN GATE
#3 (first-call approval)**: have them use the agent normally; the first brokered call
to each host pauses for approval in the dashboard. Tell them to approve it; after
that the call succeeds and (if they chose) is remembered.

### Step E — Go keyless (neutralize)

Only once verify is PROTECTED:

```bash
sesame onboard neutralize
```

This swaps the agent's real credential for a structurally-valid **dummy** (so the
agent still starts and makes calls) and keeps the real one only in Sesame. It
**refuses unless verify is PROTECTED** — don't pass `--force` to get around a failing
verify; fix verify instead. Then restart the agent so it reloads the neutralized
credential, and re-run `sesame onboard detect` to confirm the egress target now shows
`agent_holds_cred: false` — that's the keyless end state.

Reversible: `sesame onboard neutralize --undo` restores the real credential from the
journaled backup.

## The three human gates (surface each immediately — never go silent)

1. **Device approval** — `sesame login` waits on a browser approval. Give them the URL.
2. **Secret value** — adding each host's key/token happens in the dashboard, by them.
3. **First-call approval** — the first brokered call to a host pauses for their OK.

Everything else you run yourself. If a step is blocked on one of these, say so right
away and wait — do not kill a waiting command and do not loop silently.

## Safety invariants

- **Detect (read-only) before any mutation.** Re-detect / re-verify freely; both are
  read-only and idempotent.
- **Never neutralize unless verify is PROTECTED** — stripping a credential off an
  unbrokered agent just breaks it.
- **Trust `egress.targets` for the host, not the provider's brand name** (codex →
  `chatgpt.com`, not `api.openai.com`).
- **Ask, don't guess** when detect is `unknown` or a value is missing (which unit,
  which broker URL, which secret). Report detect's findings and let the human fill
  the gap.

## Quick fixes

| Symptom | Fix |
|---|---|
| detect → `seat: unknown` | Ask the human how the agent starts; use the `egress` section if present |
| First call 401 with the dummy key | Host isn't brokered yet — add the secret + `sesame proxyd reload` |
| First call 403 "no path rule" | The secret's policy is too narrow; a fresh secret on a known provider auto-gets a curated policy — re-add it, or widen the policy in the dashboard |
| verify not PROTECTED after wrap | Restart the wrapped unit; check `sesame-proxyd` is running and the secret exists |
| Agent won't start after neutralize | It refused the dummy — `sesame onboard neutralize --undo` and re-check the token shape for that provider |
