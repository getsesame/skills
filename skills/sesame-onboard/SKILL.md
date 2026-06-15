---
name: sesame-onboard
description: >-
  Walk a user through deploying a self-hosted Sesame broker into their own AWS
  account. Use when the user says "help me onboard Sesame", "deploy Sesame to my
  AWS", "set up the Sesame self-host broker", or "install Sesame on our
  infrastructure". You handle prerequisites (AWS CLI + login), explain exactly
  what each value is and how to get it (with clickable links for the Google
  step), run an interactive dry-run to capture everything, summarize the inputs,
  then run the real deploy. Never ask the user to paste secrets into the chat —
  they type those into the CLI's hidden prompts.
allowed-tools: "Bash(aws:*), Bash(sesame:*), Bash(curl:*), Bash(brew:*), Bash(unzip:*), Bash(uname:*)"
metadata:
  author: sesame
  version: 0.2.1
---

# Sesame self-host onboarding

You guide the user through `sesame deploy aws`, which provisions an EC2 + RDS in
**their** AWS account and returns an HTTPS dashboard URL. Your job: make sure the
prerequisites are met, explain each input, capture everything with a dry-run,
summarize, then deploy.

## How you run the deploy
- You run `sesame deploy aws` **non-interactively, with flags** — *except* the Google
  sign-in case, which the user runs themselves (so the client secret stays out of the
  chat; see below and Step 7). When an agent runs a command there is no TTY, so the
  CLI's interactive prompts don't fire — the flags drive everything. So your job is:
  **collect each value, then inject every value except the Google client secret as flags.**
- **AWS keys:** never handle these. The user logs into the AWS CLI themselves; you
  only verify with `aws sts get-caller-identity`.
- **Google client secret:** this is the one value you must never see. **Do not accept it
  in the chat, and never pass `--google-client-secret`.** Walk them through getting it
  (Step 4) and **confirm they have it in hand**, but when Google sign-in is on, **the
  user runs the deploy themselves** (Step 7) so the CLI prompts for the secret with
  hidden TTY input — it never passes through you or the command history. The client
  *ID* is a public identifier, so `--google-client-id` is fine for you to pass. Never
  proceed until they confirm the secret is in hand — creating it takes a few minutes and
  it can only be copied once.
- Work **one step at a time**; confirm each value before moving on.

---

## Step 0 — Sesame CLI installed?
You drive the whole deploy through the `sesame` CLI, so confirm it's present before anything else:
```bash
sesame --version
```
If "command not found", install it and re-run — don't continue until it works:
```bash
curl -fsSL https://getsesame.dev/install.sh | sh
```

## Step 1 — AWS CLI installed?
```bash
aws --version
```
If "command not found", install it:
- **macOS:** `brew install awscli` (or, no Homebrew: `curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o /tmp/AWSCLIV2.pkg && sudo installer -pkg /tmp/AWSCLIV2.pkg -target /`)
- **Linux:** `curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o /tmp/awscliv2.zip && unzip -q /tmp/awscliv2.zip -d /tmp && sudo /tmp/aws/install`

Re-run `aws --version` to confirm.

## Step 2 — Logged into AWS?
```bash
aws sts get-caller-identity
```
- **If it prints an Account + ARN:** they're logged in. **Show the user the account ID and ARN and confirm it's the account they want to deploy into.**
- **If it errors:** they need to log in. Tell the user to run **one** of these themselves (you must not handle their keys):
  - Access keys: `aws configure` (it prompts for Access Key ID, Secret, region).
  - SSO: `aws configure sso` then `aws sso login`.
  Then re-run `aws sts get-caller-identity` to confirm.

**Required IAM permissions** on that identity — attach these managed policies: `AWSCloudFormationFullAccess`, `AmazonEC2FullAccess`, `AmazonRDSFullAccess`, `IAMFullAccess`, `SecretsManagerReadWrite`, `AmazonSSMFullAccess` (the last one lets `sesame deploy update/restart/logs` reach the box later). If a policy is missing, the deploy fails with an AccessDenied for that service — relay it. The **Step 5 dry-run also prints this exact list**, so the user can check their permissions before deploying.

## Step 3 — Tier 1 (required) — collect from the user
Ask for, and confirm:
- **Admin email** — the first dashboard admin (e.g. `you@company.com`).
- **AWS region** — default `us-east-1`. Ask if they want a different one.
- **Database** — default `rds` (managed Postgres). `bundled` runs Postgres on the EC2 (cheaper, no separate DB). Default is fine for most.

These are not secrets — fine to gather in chat.

## Step 4 — Tier 2 (optional): Google Workspace sign-in
Ask: *"Do you want 'Sign in with Google' for the dashboard, or just email + password?"* If password-only, **skip to Step 5.**

If yes, walk them through it **one click at a time**:

1. **Create/select a Google Cloud project:** https://console.cloud.google.com/projectcreate (or pick an existing one).
2. **Configure the consent screen:** https://console.cloud.google.com/auth/overview → "Get started".
   - Set an app name + support email.
   - **Audience:**
     - **Have Google Workspace** → choose **Internal** (restricts sign-in to your Workspace org).
     - **No Workspace** → choose **External**, then open **Audience → Test users → Add users** and add the email they'll log in with.
3. **Create the OAuth client:** https://console.cloud.google.com/auth/clients → **Create client** → Application type **Web application** → name it "Sesame".
4. **Redirect URI — leave it for now.** It depends on the deploy's URL (which doesn't exist yet). They'll add it *after* deploy (Step 7). Saving the client without a final redirect URI is fine.
5. **Copy the Client ID and Client Secret.** (If the secret was already created and they can't re-view it, click **+ Add secret** for a fresh one.)
   - ⚠ Tell them to keep the secret handy to **type into the CLI prompt** — they should **not** paste it to you.
6. **Allowed domain:**
   - **Workspace:** their domain, e.g. `company.com` (only that Workspace's accounts can sign in).
   - **No Workspace / personal Gmail:** **leave blank** — a personal Gmail has no Workspace `hd` claim, so setting a domain would lock them out. Blank = any verified Google account allowed; they should log in with the **admin email** from Step 3.

**Readiness check — do this before moving on.** Ask the user point-blank: *"Do you have
the Client ID and Client Secret ready?"* They may not yet — that's expected; walk them
through the steps above until they do. **Note it on the side** (ID + secret in hand). Do
not start the deploy until they confirm both. You don't need them to paste the secret to
you — just confirm they have it.

## Step 5 — Dry-run to confirm (no deploy)
Build the flag list from what you collected and run it **with `--dry-run`**:
```bash
sesame deploy aws --dry-run \
  --admin-email <email> --region <region> --database <rds|bundled> \
  [--google-oauth --google-client-id <id> \
   --google-allowed-domain <domain-or-omit-if-none>]
```
It prints a **Plan** with everything resolved and **deploys nothing**. The dry-run does not need the client secret. Read the Plan back to the user and fix any value before the real run. (For non-Workspace, omit `--google-allowed-domain`.)

## Step 6 — Summary of what's needed
Before the real deploy, summarize for the user:
- ✅ AWS CLI logged in → account `<id>`
- Admin email: `<email>`
- Region: `<region>` · Database: `<rds|bundled>`
- Google sign-in: **on/off**
  - (if on) Client ID: provided · Client Secret: in hand (entered at the hidden prompt when they run the deploy) · Allowed domain: `<domain or "(none)">`
  - (if on) Redirect URI to add after deploy: `https://<broker-url>/v1/auth/google/callback`

## Step 7 — Deploy

**Password-only (no Google sign-in):** no secret is involved, so you run it — same flags, **without `--dry-run`**:
```bash
sesame deploy aws \
  --admin-email <email> --region <region> --database <rds|bundled>
```

**With Google sign-in:** the client secret must not pass through you, so **the user runs the deploy in their own terminal** — do **not** run this one yourself (you have no TTY, so the hidden secret prompt can't fire — the CLI exits with an error asking for `--google-client-secret`). The client ID is public and fine to include. Give them this command to run:
```bash
# The USER runs this in their own terminal — NOT the agent.
sesame deploy aws \
  --admin-email <email> --region <region> --database <rds|bundled> \
  --google-oauth --google-client-id <id> \
  [--google-allowed-domain <domain>]
```
The CLI then prompts `Google client secret:` — they type it there (hidden), never into the chat.

> The `--google-client-secret` flag still exists for a user scripting a non-interactive deploy (e.g. pulling the secret from their own secret store in CI). That's their choice in their own terminal. **You, the agent, never use it** — putting the secret in a command you emit is exactly what we're avoiding.

Either way it provisions the stack (~12–18 min; RDS is the long pole), then prints:
- The **dashboard URL** (e.g. `https://54-159-97-177.sslip.io`)
- The **admin setup link** (`/setup?token=…`)
- (if Google) the exact **redirect URI**.

When the **user** ran the deploy (the Google case), that output is in *their* terminal, not yours — **ask them to paste those three values back to you.** You need the dashboard URL and redirect URI to finish Step 8.

## Step 8 — Finish
- Open the **setup link** → set the admin password → sign in.
- **If Google:** go back to the OAuth client (Step 4.4), **Add URI** = the printed redirect URI, **Save** (effective in a few minutes). Then test "Continue with Google" (log in with the admin email).
- Tell the user the dashboard URL is their broker; agents point at it with `sesame login --broker-url <that URL>`.

## If something fails
- The CLI prints the failure reason (and EC2 console output on app-timeout). Relay it; don't guess.
- The stack is **not** auto-deleted on failure — fix the inputs and re-run `sesame deploy aws`.
- To tear down: `sesame deploy destroy --region <region>`.
