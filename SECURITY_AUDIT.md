# Humitron Security Audit

## What is Bandit?

[Bandit](https://github.com/PyCQA/bandit) is a tool designed to find common security issues in Python code. It scans your source code and identifies potential vulnerabilities such as:

- Use of unsafe functions (`subprocess.call(shell=True)`, `eval()`, etc.)
- Hardcoded passwords or API keys
- Insecure file operations
- SQL injection vulnerabilities
- And more

Bandit is maintained by the Python Code Quality Authority (PyCQA) and is widely used in CI/CD pipelines to catch security issues early.

## How to Run the Audit Yourself

```bash
# Install bandit
pip install bandit

# Run the scan (text output for easy reading)
bandit -r src/ -f txt -o bandit-report.txt

# Run the scan (HTML output for browser viewing)
bandit -r src/ -f html -o bandit-report.html

# Run with verbose output
bandit -r src/ -v

# Run with specific test profiles
bandit -r src/ -p high_severity_tests

# Open the HTML report in your browser
open bandit-report.html  # macOS
xdg-open bandit-report.html  # Linux
start bandit-report.html  # Windows
```

## Audit Results Summary

- **Date:** 2024-06-29
- **Target:** `src/` directory
- **Files Scanned:** 15
- **Lines Analyzed:** 2,847
- **HIGH Severity Issues:** 0
- **MEDIUM Severity Issues:** 2 (reviewed and mitigated)
- **LOW Severity Issues:** 3 (informational / false positives)

## Issues Found and Mitigations

### Medium Severity

1. **subprocess call with shell=True** (`src/humitron/tools/bash.py`)
   - **Finding:** B602 - Using `shell=True` in subprocess calls
   - **Mitigation:** This is intentional. The bash_execute tool needs `shell=True` to function. However, ALL commands pass through `is_command_dangerous()` validation first. The safety module blocks: `rm -rf /`, `sudo`, `chmod 777`, `dd`, `mkfs`, fork bombs, shutdown, reboot, and command chaining attacks.
   - **Risk:** Low - Multi-layer defense with command pattern blacklisting

2. **Function call with shell=True** (`src/humitron/tools/bash.py`)
   - **Finding:** B604 - Same as above, flagged differently
   - **Mitigation:** Identical defense mechanisms apply
   - **Risk:** Low

### Low Severity (False Positives)

1. **B108** - "Insecure usage of temp directory" - False positive. Paths are always workspace-scoped.
2. **B105** - "Hardcoded password" - False positive. The string `cloud_api_key` is a configuration key name, not a password.
3. **B101** - "Use of assert" - Development-time assertion only. Not in production code paths.

## Current Security Status

✅ **NO HIGH-SEVERITY ISSUES FOUND**

All medium-severity findings are intentional design decisions with documented mitigations. The bash_execute tool is core functionality protected by:

1. **Command Pattern Blacklist:** 14 patterns block known dangerous commands
2. **Chain Detection:** Commands using `&&`, `||`, `;` are recursively checked
3. **Path Sandboxing:** All file operations restricted to workspace directory
4. **Timeout Limits:** Commands auto-kill after configurable timeout (default: 30s)

## What You Should Check When Auditing

When running your own audit, pay special attention to:

1. **`src/humitron/tools/bash.py`** - The bash_execute tool. Understand how command filtering works.
2. **`src/humitron/utils/safety.py`** - The safety module. Review the blocked patterns.
3. **`src/humitron/tools/file_ops.py`** - File operations. Ensure path sandboxing is working.
4. **`src/humitron/agent.py`** - The ReAct loop. Understand how agent decisions are made.
5. **`src/humitron/config/loader.py`** - Configuration loading. Check for secrets management.

## Continuous Security

This audit should be re-run:

- Every time new dependencies are added
- Every time the codebase is modified
- Before every release
- As part of CI/CD pipeline (see `.github/workflows/ci.yml`)

## Reporting Security Issues

If you find a security vulnerability during your audit, please **DO NOT** open a public issue.

Email: **security@app:humi** (replace : with the domain)

See `SECURITY.md` for our full vulnerability disclosure policy.

---

*"Trust, but verify. Then verify again."*