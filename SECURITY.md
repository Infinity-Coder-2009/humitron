# 🔒 Security Policy

## Table of Contents
- [Supported Versions](#supported-versions)
- [Audit Before You Run](#-audit-before-you-run)
- [How to Report a Vulnerability](#-how-to-report-a-vulnerability)
- [Disclosure Policy](#disclosure-policy)
- [Security Best Practices](#-security-best-practices-for-users)
- [Dependency Auditing](#-dependency-auditing)
- [Security Features](#-security-features-in-humitron)

---

## Supported Versions

We only support the latest release. Please update to the newest version to ensure you have all security patches.

| Version | Supported |
|---------|-----------|
| Latest | ✅ |
| Older versions | ❌ |

---

## 🔍 Audit Before You Run

**Never run code you haven't audited.** This applies to Humitron as much as any other software. Here's how to verify Humitron's safety:

### 1. Review the Dependency Lock File
All dependencies are pinned to exact versions in [`requirements-lock.txt`](requirements-lock.txt). This file is generated from `requirements.txt` using `pip-tools` and contains the exact versions of every package Humitron depends on.

**Verify dependencies:**
```bash
# Check for known vulnerabilities
pip-audit -r requirements-lock.txt

# Review what each dependency does
pip show pydantic httpx fastapi
```

### 2. Review the Security Audit
A complete security audit is available in [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md). This report:
- Lists all findings from the Bandit security scanner
- Explains each issue and how it was resolved
- Shows the current security status (No high-severity issues found)

**Run your own audit:**
```bash
pip install bandit
bandit -r src/ -f html -o bandit-report.html
open bandit-report.html  # Review the results
```

### 3. Inspect the Source Code
Every line of Humitron is open source and auditable:
- **No binaries** - All code is plain Python
- **No obfuscation** - Clean, documented code with docstrings
- **No telemetry** - Nothing phones home
- **No analytics** - No tracking of any kind

### 4. Security Audit Report
See the full audit at: [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md)

---

## 🚨 How to Report a Vulnerability

If you discover a security vulnerability, please **DO NOT** open a public issue on GitHub.

Email us at **security@humitron.com**

We will:
- Acknowledge your report within **48 hours**
- Investigate and validate the issue
- Provide a timeline for the fix
- Give you credit for the discovery (if you wish)

### What to Include in Your Report
- A clear description of the vulnerability
- Steps to reproduce (if applicable)
- Affected versions
- Potential impact
- Any suggested fixes

---

## Disclosure Policy

- We will notify users about security fixes in the release notes
- Critical fixes will be pushed as emergency patches
- We will never expose user data or breach privacy
- All security fixes are published in [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md)

---

## 🛡️ Security Best Practices for Users

1. **Always audit before you run** - Read the code, check dependencies
2. **Use the lock file** - Install from `requirements-lock.txt` for exact dependency versions
3. **Run in a sandbox** - Use Docker or a VM for additional isolation
4. **Never share your API keys** with untrusted agents or services
5. **Set budget caps** when using cloud mode (OpenAI, Anthropic) to prevent runaway costs
6. **Keep dependencies updated** - Run `pip-audit` regularly
7. **Build from source** - Don't run pre-built binaries you haven't verified

---

## 📦 Dependency Auditing

### Lock File
The [`requirements-lock.txt`](requirements-lock.txt) file contains pinned versions of all dependencies. Install using this file for reproducible builds:

```bash
pip install -r requirements-lock.txt
```

### Regular Auditing
```bash
# Security scanner (Python code)
bandit -r src/

# Dependency vulnerability scanner
pip-audit -r requirements-lock.txt

# Both together
make security-audit
```

---

## 🔐 Security Features in Humitron

| Feature | Description | Status |
|---------|-------------|--------|
| **Command Filtering** | 14+ regex patterns block dangerous commands (rm -rf /, sudo, chmod 777, fork bombs, etc.) | ✅ Active |
| **Path Sandboxing** | All file operations restricted to workspace directory | ✅ Active |
| **Command Chain Detection** | Chained commands (&&, \|\|, ;) are recursively checked | ✅ Active |
| **Timeout Protection** | All operations have configurable timeouts (default 30s) | ✅ Active |
| **Token Budgeting** | Prevents runaway LLM costs and context overload | ✅ Active |
| **No Telemetry** | No data leaves your machine | ✅ Active |
| **No Analytics** | No tracking of any kind | ✅ Active |
| **Open Source** | Every line audit-able | ✅ Active |
| **Docker Sandbox** | Isolated container with non-root user | ✅ Available |
| **Security Audit Report** | Complete Bandit audit in SECURITY_AUDIT.md | ✅ Available |
| **Dependency Lock File** | Pinned exact versions for reproducible builds | ✅ Available |

---

**Last Updated:** 2024-07-16  
**Next Review:** Before v0.3.0 release

For questions about Humitron's security, contact **security@humitron.com**