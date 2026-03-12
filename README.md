# Corque AI Agent

Corque is a local-first personal AI agent with practical tooling (todo, email, weather, web, code, shell, memory) and built-in human approval for sensitive actions.

## Problem

Most personal AI assistants are either:
- **Too limited** (cannot take real actions), or
- **Too risky** (can execute actions without enough control).

Corque targets a middle ground: real automation with explicit guardrails.

## Architecture

High-level flow:
1. User request enters the LangGraph/LangChain agent.
2. Tool middleware injects available skills/tools.
3. Agent selects tools and executes.
4. Sensitive tools (`sendEmail`, `writeFile`, `runShellCommand`, `runCode`) pause for human approval.
5. Final response is returned.

Key components:
- `core/agent.py` – agent construction, tools, human-in-the-loop middleware.
- `tools/` – modular tool implementations.
- `config/settings.py` – env-driven settings.
- `api_server.py` – FastAPI backend for desktop UI.
- `corque-ui/` – Electron desktop client.

## Safety

Corque includes multiple safety layers:
- **Human approval flow** for sensitive operations.
- **Shell hardening** in `runShellCommand`:
  - command allowlist (configurable)
  - denylist pattern blocking
  - sandboxed working directory
  - append-only audit log (`data/shell_audit.log` by default)
- **Workspace isolation** for generated code execution.

Shell hardening can be configured through `.env` (see `.env.example`).

## Metrics

An offline-friendly MVP evaluation harness is included under `evaluation/`.

It runs 20+ deterministic checks covering:
- code parsing/validation helpers
- filename/path sanitization
- shell guardrail behavior
- basic file IO/system tool behavior

Outputs:
- `evaluation/evaluation_report.md`
- Summary metrics: success rate, average latency, p95 latency, tool-error count.

Run:
```bash
python evaluation/run_evaluation.py
```

## Demo

Typical demo prompts:
- "Add a todo for tomorrow: submit internship application"
- "What is the weather in Pittsburgh?"
- "Draft an email to recruiter@example.com about interview availability"
- "Generate a Python script in workspace to parse CSV and run it"

Safety demo:
- Ask Corque to run a shell command; verify approval prompt appears.
- Try a blocked command pattern (e.g., `echo ok && echo nope`) and confirm denylist rejection.
- Open `data/shell_audit.log` to inspect execution decisions.

## Quickstart

### 1) Prerequisites
- Python 3.9+
- Optional UI: Node.js + npm
- Model runtime you plan to use (Ollama/OpenAI-compatible backend depending on your configuration)

### 2) Install dependencies
```bash
pip install -r requirements-full.txt
```

Windows helper installer:
```bat
dependencysetup.bat
```

### 3) Configure environment
Copy sample env and edit values:
```bash
copy .env.example .env
```

Minimum recommended setup:
- `DEDALUS_API_KEY` (if using default hosted model path)
- Email fields (`EMAIL_USER`, `EMAIL_PASS`, `SMTP_SERVER`, `IMAP_SERVER`) only if you use email tools
- `TAVILY_API_KEY` only if you use web/news tools

Optional shell security tuning:
- `SHELL_ALLOWED_COMMANDS`
- `SHELL_DENIED_PATTERNS`
- `SHELL_SANDBOX_ROOT`
- `SHELL_AUDIT_LOG_PATH`
- `SHELL_REQUIRE_ALLOWLIST`
- `SHELL_ENFORCE_SANDBOX`

### 4) Run CLI agent
```bash
python main.py
```

### 5) Run API server (for UI)
```bash
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

### 6) Run Electron UI (optional)
```bat
start.bat
```

## Configuration Notes

Main config is in `config/settings.py` and environment variables.

Defaults are intentionally conservative for shell execution:
- allowlist required (`SHELL_REQUIRE_ALLOWLIST=true`)
- sandbox enforced (`SHELL_ENFORCE_SANDBOX=true`)

If you need additional commands for trusted local workflows, add them to `SHELL_ALLOWED_COMMANDS`.

## Project Structure

```text
Corque-AI-agent/
├── core/
├── tools/
├── middleware/
├── config/
├── evaluation/
├── corque-ui/
├── api_server.py
├── main.py
└── README.md
```

## License

See `LICENSE`.
