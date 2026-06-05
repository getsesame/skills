---
name: sesame-onboard
description: >-
  Deploy a self-hosted Sesame broker onto the user's own AWS account. Use when the
  user says "help me onboard Sesame", "deploy Sesame to my AWS", "set up the Sesame
  self-host broker", or "install Sesame on our infrastructure". Drives the `sesame`
  CLI to provision EC2 + RDS + an HTTPS dashboard. The user fills secrets into a
  local .env that YOU must never read — secrets never enter the conversation.
allowed-tools: "Bash(sesame:*), Bash(aws:*), Bash(curl:*)"
metadata:
  author: sesame
  version: 0.1.0
---

# Sesame self-host onboarding

You deploy a self-hosted Sesame broker into the **user's own AWS account** using the
`sesame` CLI. The deploy creates an EC2 instance + RDS Postgres and returns an HTTPS
dashboard URL.

## The one hard rule: stay secret-blind

The user puts all credentials into a local **`.env`** file. **You never read it.**
- ❌ Never `cat`, `Read`, `head`, `grep`, print, or echo `.env`.
- ❌ Never ask the user to paste API keys, client secrets, or passwords into the chat.
- ✅ You only run `sesame` commands; the **CLI** reads `.env`, and secret values are
  `NoEcho` in the deploy output. Secrets never enter your context.
- AWS credentials come from the user's **own logged-in AWS CLI** — never handle them.

## Steps

### 1. Preflight
```bash
sesame --version          # if "command not found": curl -fsSL https://getsesame.dev/install.sh | sh
aws sts get-caller-identity   # must succeed — confirms the user is logged into the right AWS account
```
Show the user the AWS account/ARN and confirm it's the account they want to deploy into.

### 2. Scaffold the config
```bash
sesame deploy init
```
This writes `./.env` and opens it in their editor. Tell the user:
> Fill in **Tier 1** (required). Uncomment + fill **Tier 2** (Google Workspace login)
> and **Tier 3** (email invites) only if you want them. Save the file, then tell me to continue.

The tiers:
- **Tier 1 — required:** admin email, region, database (`rds` default), image tag. (AWS creds are *not* in the file — they come from their AWS CLI.)
- **Tier 2 — optional, Google Workspace login:** Google OAuth Client ID + Secret + allowed domain (+ domain-auto-join). They create the OAuth client in Google Cloud Console; after deploy, they paste the printed redirect URI into it.
- **Tier 3 — optional, email invites:** SMTP host/port/user/pass/from. Workspace users can point at `smtp.gmail.com` (app password) or the Workspace SMTP relay.

**A blank/commented tier is simply skipped.** Wait for the user to say they've saved it. Do **not** read the file to "check" it.

### 3. Deploy
```bash
sesame deploy aws
```
It auto-reads `./.env`, validates, and provisions (~12–18 min; RDS is the long pole). It prints a live progress bar, then the **dashboard URL** and the **`/setup?token=…` admin link**.

### 4. Hand off
Relay to the user (from the command's stdout — not the file):
- The **dashboard URL** (e.g. `https://54-12-34-56.sslip.io`).
- The **admin setup link** — they open it once to set the admin password.
- If Tier 2: the **redirect URI** to add to their Google OAuth client.
- Tell them to **delete `.env`** now that the deploy is done (it may contain secrets).

## Day-2 (optional)
- `sesame deploy logs` — fetch broker logs.
- `sesame deploy update` — pull a new image and restart (migrations apply on restart).
- `sesame deploy destroy` — tear the stack down.

## If something fails
- The CLI prints the failure reason and (on app-timeout) the EC2 console output. Relay it; don't guess.
- "Admin email is required" → the user left Tier 1 blank in `.env`; ask them to fill it and save.
- "No AWS credentials" → they aren't logged into AWS CLI; have them run their AWS login.
- The stack is **not** auto-deleted on failure, so you can re-run `sesame deploy aws` after fixing `.env`.
