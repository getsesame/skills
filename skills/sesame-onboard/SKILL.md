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
  version: 0.2.0
---

# Sesame self-host onboarding

You guide the user through `sesame deploy aws`, which provisions an EC2 + RDS in
**their** AWS account and returns an HTTPS dashboard URL. Your job: make sure the
prerequisites are met, explain each input, capture everything with a dry-run,
summarize, then deploy.

## How you run the deploy
- You run `sesame deploy aws` **non-interactively, with flags.** When an agent runs a
  command there is no TTY, so the CLI's interactive prompts don't fire — the flags
  drive everything. So your job is: **collect each value, then inject them as flags.**
- **AWS keys:** never handle these. The user logs into the AWS CLI themselves; you
  only verify with `aws sts get-caller-identity`.
- **Google client secret:** don't *demand* they paste it. Walk them through getting it
  (Step 4) and **confirm they have it ready** before deploying. If they paste it,
  that's fine — pass it via `--google-client-secret`. If they'd rather it not enter the
  chat, use the **secret-private fallback** in Step 7 (they run the deploy and type it
  into the hidden prompt). Either way, **never proceed until they confirm the key is in
  hand** — creating it takes a few minutes and the secret can only be copied once.
- Work **one step at a time**; confirm each value before moving on.

---

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
   - ⚠️ Tell them to keep the secret handy to **type into the CLI prompt** — they should **not** paste it to you.
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
  [--google-oauth --google-client-id <id> --google-client-secret <secret> \
   --google-allowed-domain <domain-or-omit-if-none>]
```
It prints a **Plan** with everything resolved (secrets shown only as `set`) and **deploys nothing**. Read the Plan back to the user and fix any value before the real run. (For non-Workspace, omit `--google-allowed-domain`.)

## Step 6 — Summary of what's needed
Before the real deploy, summarize for the user:
- ✅ AWS CLI logged in → account `<id>`
- Admin email: `<email>`
- Region: `<region>` · Database: `<rds|bundled>`
- Google sign-in: **on/off**
  - (if on) Client ID: provided · Client Secret: provided · Allowed domain: `<domain or "(none)">`
  - (if on) Redirect URI to add after deploy: `https://<broker-url>/v1/auth/google/callback`

## Step 7 — Deploy
Same flags, **without `--dry-run`**:
```bash
sesame deploy aws \
  --admin-email <email> --region <region> --database <rds|bundled> \
  [--google-oauth --google-client-id <id> --google-client-secret <secret> \
   --google-allowed-domain <domain>]
```
It provisions the stack (~12–18 min; RDS is the long pole), then prints:
- The **dashboard URL** (e.g. `https://54-159-97-177.sslip.io`)
- The **admin setup link** (`/setup?token=…`)
- (if Google) the exact **redirect URI**.

**Secret-private fallback:** if the user doesn't want the Google client secret to enter the chat or the command, give them the command **without** `--google-client-id/--google-client-secret` and have them run it **themselves in their own terminal** — there, it's a TTY, so the CLI will interactively prompt for the client ID + secret (hidden input).

## Step 8 — Finish
- Open the **setup link** → set the admin password → sign in.
- **If Google:** go back to the OAuth client (Step 4.4), **Add URI** = the printed redirect URI, **Save** (effective in a few minutes). Then test "Continue with Google" (log in with the admin email).
- Tell the user the dashboard URL is their broker; agents point at it with `sesame login --broker-url <that URL>`.

## If something fails
- The CLI prints the failure reason (and EC2 console output on app-timeout). Relay it; don't guess.
- The stack is **not** auto-deleted on failure — fix the inputs and re-run `sesame deploy aws`.
- To tear down: `sesame deploy destroy --region <region>`.
