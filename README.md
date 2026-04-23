# Sesame Skills

Agent skills for [Sesame](https://github.com/getsesame) — a user-controlled broker that proxies authenticated HTTP API calls, so agents don't need to handle auth material directly.

## Install

```bash
npx skills add getsesame/skills
```

This auto-detects your agent platform (Claude Code, Codex, Cursor, etc.) and installs the skill to the right location.

## What it does

When installed, the Sesame skill teaches your AI agent to:

1. Route authenticated HTTP requests through `secretctl request` instead of `curl`
2. Check which API hostnames are configured via `secretctl hostnames`
3. Handle the approval flow the first time an agent reaches a new hostname
4. Leave auth headers to the broker — the agent never needs to construct them

## Prerequisites

- **secretctl** CLI installed — see https://getsesame.dev for install instructions
- Agent registered with your Sesame broker: `secretctl login`
- At least one hostname configured in the Sesame dashboard

## Available skills

| Skill | Description |
|-------|-------------|
| [sesame](skills/sesame/) | Proxy authenticated API calls through the Sesame broker via `secretctl` |
