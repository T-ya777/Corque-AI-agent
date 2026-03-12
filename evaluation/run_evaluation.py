import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.codeGenTools import (  # noqa: E402
    parse_code_response,
    _strip_markdown,
    _detect_default_filename,
    _extract_requested_filenames,
    _validate_generated_files,
    _sanitize_filename,
)
from tools.fileIOTools import readFile, writeFile, runShellCommand, systemInfo  # noqa: E402


def write_read_roundtrip(path: str, text: str) -> str:
    writeFile.invoke({"filePath": path, "content": text})
    output = readFile.invoke({"filePath": path})
    try:
        p = ROOT / path
        if p.exists():
            p.unlink()
    except Exception:
        pass
    return output


CALLABLES = {
    "parse_code_response": lambda *a: parse_code_response(*a),
    "_strip_markdown": lambda *a: _strip_markdown(*a),
    "_detect_default_filename": lambda *a: _detect_default_filename(*a),
    "_extract_requested_filenames": lambda *a: _extract_requested_filenames(*a),
    "_validate_generated_files": lambda *a: _validate_generated_files(*a),
    "_sanitize_filename": lambda *a: _sanitize_filename(*a),
    "readFile": lambda *a: readFile.invoke({"filePath": a[0]}),
    "runShellCommand": lambda *a: runShellCommand.invoke(
        {"command": a[0], "workingDirectory": a[1] if len(a) > 1 else ""}
    ),
    "systemInfo": lambda *a: systemInfo.invoke({}),
    "write_read_roundtrip": lambda *a: write_read_roundtrip(*a),
}


def assert_result(result, assertion):
    op = assertion["op"]
    value = assertion.get("value")

    if op == "contains":
        return value in str(result)
    if op == "equals":
        return result == value
    if op == "dict_has_key":
        return isinstance(result, dict) and value in result
    if op == "dict_value_contains":
        return isinstance(result, dict) and assertion["key"] in result and value in str(result[assertion["key"]])
    if op == "list_contains":
        return isinstance(result, list) and value in result
    if op == "list_len":
        return isinstance(result, list) and len(result) == value
    if op == "tuple_first_equals":
        return isinstance(result, tuple) and len(result) > 0 and result[0] == value
    return False


def run_task(task):
    fn = CALLABLES[task["call"]]
    args = task.get("args", [])

    start = time.perf_counter()
    error = ""
    try:
        result = fn(*args)
        ok = all(assert_result(result, assertion) for assertion in task.get("assertions", []))
    except Exception as exc:
        result = f"Exception: {exc}"
        ok = False
        error = str(exc)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    tool_error = isinstance(result, str) and result.strip().lower().startswith("error")

    return {
        "id": task["id"],
        "ok": ok,
        "duration_ms": duration_ms,
        "tool_error": tool_error,
        "error": error,
        "result_preview": str(result)[:240],
    }


def render_report(results, out_path: Path):
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    success_rate = (passed / total * 100.0) if total else 0.0
    avg_latency = sum(r["duration_ms"] for r in results) / total if total else 0.0
    p95_index = max(0, int(total * 0.95) - 1)
    sorted_latency = sorted(r["duration_ms"] for r in results)
    p95_latency = sorted_latency[p95_index] if sorted_latency else 0.0
    tool_errors = sum(1 for r in results if r["tool_error"])

    lines = [
        "# Corque MVP Evaluation Report",
        "",
        "## Summary",
        f"- Total tasks: **{total}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{failed}**",
        f"- Success rate: **{success_rate:.2f}%**",
        f"- Avg latency: **{avg_latency:.2f} ms**",
        f"- P95 latency: **{p95_latency:.2f} ms**",
        f"- Tool errors observed: **{tool_errors}**",
        "",
        "## Task Results",
        "| Task ID | Status | Latency (ms) | Tool Error | Preview |",
        "|---|---:|---:|---:|---|",
    ]

    for r in results:
        status = "PASS" if r["ok"] else "FAIL"
        preview = r["result_preview"].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {r['id']} | {status} | {r['duration_ms']:.2f} | {r['tool_error']} | {preview} |")

    out_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    tasks_path = Path(__file__).resolve().parent / "tasks.json"
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))

    results = [run_task(task) for task in tasks]

    report_path = Path(__file__).resolve().parent / "evaluation_report.md"
    render_report(results, report_path)

    print(f"Evaluation complete. Report saved to: {report_path}")
