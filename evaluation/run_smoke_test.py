from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agent import Agent


@dataclass
class SmokeCase:
    id: str
    prompt: str
    expected_contains: list[str]


CASES: list[SmokeCase] = [
    SmokeCase(
        id="smoke_001_math",
        prompt="What is 2+2?",
        expected_contains=["4"],
    ),
    SmokeCase(
        id="smoke_002_todo_add",
        prompt="Add a todo for tomorrow: smoke-test-task",
        expected_contains=["todo", "smoke-test-task"],
    ),
    SmokeCase(
        id="smoke_003_todo_read",
        prompt="Show my todos in the next 3 days",
        expected_contains=["smoke-test-task"],
    ),
    SmokeCase(
        id="smoke_004_shell_hitl",
        prompt="Run shell command: echo smoke-check",
        expected_contains=["needs approval"],
    ),
    SmokeCase(
        id="smoke_005_system_info",
        prompt="What system are you running on? Use your tool if needed.",
        expected_contains=["system"],
    ),
    SmokeCase(
        id="smoke_006_time",
        prompt="What is the current UTC time?",
        expected_contains=["UTC"],
    ),
    SmokeCase(
        id="smoke_007_todo_recent",
        prompt="What is my most recent todo?",
        expected_contains=["smoke-test-task"],
    ),
    SmokeCase(
        id="smoke_008_shell_block",
        prompt="Run shell command: echo ok && echo nope",
        expected_contains=["needs approval"],
    ),
]


def _check_pass(response: str, expected: list[str]) -> tuple[bool, str]:
    body = (response or "").lower()
    for token in expected:
        if token.lower() not in body:
            return False, f"missing token: {token}"
    return True, ""


def render_report(rows: list[dict], out_path: Path) -> None:
    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    failed = total - passed
    avg_ms = round(sum(r["latency_ms"] for r in rows) / total, 2) if total else 0.0
    p95_index = max(0, int(total * 0.95) - 1)
    p95 = sorted(r["latency_ms"] for r in rows)[p95_index] if total else 0.0

    lines: list[str] = [
        "# Corque Smoke Test Report",
        "",
        "## Summary",
        f"- Total cases: **{total}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{failed}**",
        f"- Success rate: **{(passed / total * 100.0 if total else 0.0):.2f}%**",
        f"- Avg latency: **{avg_ms} ms**",
        f"- P95 latency: **{p95:.2f} ms**",
        "",
        "## Case Results",
        "| ID | Status | Latency (ms) | Check | Response Preview |",
        "|---|---:|---:|---|---|",
    ]

    for row in rows:
        status = "PASS" if row["passed"] else "FAIL"
        preview = row["response"].replace("\n", " ").replace("|", "\\|")[:220]
        lines.append(
            f"| {row['id']} | {status} | {row['latency_ms']:.2f} | {row['check']} | {preview} |"
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    agent = Agent()
    rows: list[dict] = []

    for case in CASES:
        start = time.perf_counter()
        response = agent.ask(case.prompt, interactive=False)
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        passed, check = _check_pass(response, case.expected_contains)

        rows.append(
            {
                "id": case.id,
                "prompt": case.prompt,
                "response": str(response),
                "latency_ms": elapsed,
                "passed": passed,
                "check": check or "ok",
            }
        )

    report_path = Path(__file__).resolve().parent / "smoke_test_report.md"
    render_report(rows, report_path)
    print(f"Smoke test complete. Report saved to: {report_path}")


if __name__ == "__main__":
    main()
