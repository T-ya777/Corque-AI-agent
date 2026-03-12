# Corque Smoke Test Report

## Summary
- Total cases: **8**
- Passed: **8**
- Failed: **0**
- Success rate: **100.00%**
- Avg latency: **4430.77 ms**
- P95 latency: **6719.35 ms**

## Case Results
| ID | Status | Latency (ms) | Check | Response Preview |
|---|---:|---:|---|---|
| smoke_001_math | PASS | 1957.69 | ok | 2 + 2 = 4 |
| smoke_002_todo_add | PASS | 11830.73 | ok | Todo added successfully! I've created a task called "smoke-test-task" due tomorrow (March 13, 2026). |
| smoke_003_todo_read | PASS | 6719.35 | ok | Here are your todos for the next 3 days:  **Today (March 12, 2026)** - **smoke-test-task** (ID: 2)   - Due: 8:00 PM (EST)   - Status: Pending  **Tomorrow (March 13, 2026)** - **test-corque-mvp** (ID: 1)   - Due: 8:00 AM  |
| smoke_004_shell_hitl | PASS | 1841.64 | ok | Action 'runShellCommand' needs approval before continuing. |
| smoke_005_system_info | PASS | 2987.13 | ok | I'm running on a **Windows** system (win32). |
| smoke_006_time | PASS | 3279.39 | ok | The current UTC time is **2026-03-12 17:40:15.410957+00:00**. |
| smoke_007_todo_recent | PASS | 4666.53 | ok | Your most recent todo is:  **smoke-test-task** (ID: 2) - Status: Pending - Due: 8:00 PM (EST) today - Created: 1:40 PM (EST) today |
| smoke_008_shell_block | PASS | 2163.74 | ok | Action 'runShellCommand' needs approval before continuing. |
