# Sesame Skills

Agent skills for [Sesame](https://github.com/getsesame) — a secret broker that lets AI agents make authenticated API calls without ever seeing credentials.

## Install

```bash
npx skills add getsesame/skills
```

This auto-detects your agent platform (Claude Code, Codex, Cursor, etc.) and installs the skill to the right location.

## What it does

When installed, the Sesame skill teaches your AI agent to:

1. Route authenticated HTTP requests through `secretctl request` instead of `curl`
2. Check which API hostnames have secrets configured via `secretctl hostnames`
3. Handle approval flows when accessing a new API for the first time
4. Never hardcode, log, or store API keys — the broker injects credentials server-side

## Prerequisites

- **secretctl** CLI installed: `uv tool install sesame-ctl`
- Agent registered with your Sesame broker: `secretctl login`
- At least one secret configured in the Sesame dashboard for the hostname you want to reach

## Available skills

| Skill | Description |
|-------|-------------|
| [sesame](skills/sesame/) | Secure API credential injection via secretctl |
