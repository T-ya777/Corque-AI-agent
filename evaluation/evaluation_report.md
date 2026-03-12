# Corque MVP Evaluation Report

## Summary
- Total tasks: **22**
- Passed: **22**
- Failed: **0**
- Success rate: **100.00%**
- Avg latency: **0.74 ms**
- P95 latency: **0.56 ms**
- Tool errors observed: **4**

## Task Results
| Task ID | Status | Latency (ms) | Tool Error | Preview |
|---|---:|---:|---:|---|
| parse_single_py | PASS | 0.19 | False | {'main.py': "print('ok')"} |
| parse_multi_files | PASS | 0.01 | False | {'a.py': 'A=1', 'b.js': 'console.log(1)'} |
| strip_markdown | PASS | 0.00 | False | print(1) |
| detect_default_py | PASS | 0.04 | False | main.py |
| detect_default_js | PASS | 0.00 | False | main.js |
| extract_requested_files | PASS | 0.15 | False | ['api/main.py', 'ui/app.js'] |
| validate_generated_pass | PASS | 0.00 | False | (True, '') |
| validate_generated_fail_missing | PASS | 0.00 | False | (False, 'Expected at least 2 files, but got 1.\nMissing files: utils.py') |
| sanitize_filename_windows_chars | PASS | 0.01 | False | badnamefile.py |
| sanitize_filename_nested | PASS | 0.00 | False | folder/sub/main.py |
| shell_allowlisted_echo | PASS | 12.03 | False | The command 'echo corque-eval' was executed successfully with output: corque-eval  |
| shell_denylist_chain | PASS | 0.53 | True | Error: command blocked by denylist pattern '&&'. |
| shell_not_allowlisted | PASS | 0.37 | True | Error: command 'ipconfig' is not allowlisted. Update SHELL_ALLOWED_COMMANDS in .env if this command is needed. |
| shell_path_escape | PASS | 0.56 | True | Error: working directory is outside the configured sandbox root. |
| read_missing_file | PASS | 0.23 | True | Error happens in reading the file: [Errno 2] No such file or directory: '__this_file_should_not_exist__.txt' |
| write_and_read_roundtrip | PASS | 1.78 | False | hello-eval |
| system_info | PASS | 0.46 | False | The system information is: win32 |
| parse_no_markers | PASS | 0.02 | False | {'main.py': "print('fallback')"} |
| extract_no_files | PASS | 0.01 | False | [] |
| validate_fence_fail | PASS | 0.00 | False | (False, 'Found leftover markdown fences in files: main.py') |
| detect_default_unknown | PASS | 0.00 | False | main.txt |
| sanitize_empty | PASS | 0.00 | False |  |