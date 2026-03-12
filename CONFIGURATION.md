# Configuration Guide

## Setup in 60 seconds

1. Copy template:
   ```bat
   copy .env.example .env
   ```
2. Open `.env` and set required values.
3. Start Corque with `python main.py`.

## Required vs Optional

### Required (default hosted model path)
- `DEDALUS_API_KEY`

### Required only if using email tools
- `EMAIL_USER`
- `EMAIL_PASS`
- `SMTP_SERVER`
- `IMAP_SERVER`

### Optional
- `TAVILY_API_KEY` (web/news)
- `SENDER_NAME`, `USER_NAME`, `REGION`

## Shell Security Settings (runShellCommand)

- `SHELL_SANDBOX_ROOT` – command execution root folder.
- `SHELL_AUDIT_LOG_PATH` – append-only audit log output.
- `SHELL_REQUIRE_ALLOWLIST` – `true`/`false`.
- `SHELL_ENFORCE_SANDBOX` – `true`/`false`.
- `SHELL_ALLOWED_COMMANDS` – comma-separated command names.
- `SHELL_DENIED_PATTERNS` – comma-separated blocked patterns.

Recommended defaults are already included in `.env.example`.
