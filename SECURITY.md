# Security Policy

## Audit Before You Run

**Humitron is 100% open source and auditable. But you should never trust any code blindly—including this one.**

Before running Humitron, we strongly recommend:

1. **Review the lock file:** `requirements-lock.txt` contains every dependency with pinned versions. Audit each one.
2. **Review the security audit:** `SECURITY_AUDIT.md` contains Bandit scanner results and explains any findings.
3. **Run your own scan:**
   ```bash
   pip install bandit
   bandit -r src/ -f html -o bandit-report.html
   open bandit-report.html
   ```
4. **Read the code:** Every file in this repository is human-readable. There are no binaries, no obfuscated code, and no hidden surprises.
5. **Run in isolation:** Use Docker or a VM for your first run.

## Supported Versions

We only support the latest release. Please update to the newest version to ensure you have all security patches.

| Version | Supported |
|---------|-----------|
| Latest | ✅ |
| Older versions | ❌ |

## How to Report a Vulnerability

If you discover a security vulnerability, please **DO NOT** open a public issue on GitHub.

Instead, email us at **security@app:humitron.com**.

We will:
- Acknowledge your report within **48 hours**
- Investigate and validate the issue
- Provide a timeline for the fix
- Give you credit for the discovery (if you wish)
- Add the finding to SECURITY_AUDIT.md for transparency

## Disclosure Policy

- We will notify users about security fixes in the release notes
- Critical fixes will be pushed as emergency patches
- We will never expose user data or breach privacy
- All security findings are documented in `SECURITY_AUDIT.md`

## Security Best Practices for Users

1. **Always use the latest version**
2. **Install from the lock file:** `pip install -r requirements-lock.txt`
3. **Run Humitron in a sandboxed environment** (Docker or VM) for sensitive tasks
4. **Never share your API keys** with untrusted agents
5. **Set budget caps** when using cloud mode to prevent runaway costs
6. **Audit dependencies** with `pip-audit` or `bandit`
7. **Review the code** before building or running

## Dependency Verification

All dependencies are pinned in `requirements-lock.txt`. You can verify package integrity:

```bash
# Install from lock file
pip install -r requirements-lock.txt

# Check for known vulnerabilities
pip install pip-audit
pip-audit

# Verify package hashes
pip hash <package-name>

# Check dependency tree
pipdeptree
```

---

Thank you for helping keep Humitron safe and trustworthy.