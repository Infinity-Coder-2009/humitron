# Humitron: Local-First AI Agent

**Humitron is the AI agent that runs on your terms.**

- **Runs 100% free on your own machine** — Uses Ollama for local inference
- **Uses any model you want** — Ollama, OpenAI, Claude, Gemini, or OpenRouter
- **No subscriptions. No lock-in.** — Just an AI that works for you
- **Desktop native** — Built for macOS, Windows, and Linux

---

## 🔒 Security & Trust

**Humitron is open-source and 100% auditable. However, I strongly recommend:**

1. **Never run code you haven't audited** — including this one.
2. **Run it in a sandbox** (Docker, VM) if you want to test it safely.
3. **Review the dependencies** by checking `requirements-lock.txt`.
4. **Review the security audit** in `SECURITY_AUDIT.md`.
5. **Review every file** in this repository before building.

### Verify This Repository

To verify this repository is legitimate:

1. **Check the commit history** — every change is visible.
2. **Review the code yourself** — there are no binaries or obfuscated files.
3. **Build from source** — don't run pre-built binaries.
4. **Run in a sandbox** — use Docker or a VM.
5. **Ask questions** — open an issue or join the community.

---

## 📦 Safe Installation

```bash
# Clone the repository
git clone https://github.com/humitron/humitron.git
cd humitron

# AUDIT THE CODE FIRST. Read every file. Understand what it does.

# Install from the lock file (always use the lock file!)
pip install -r requirements-lock.txt

# Run security audit yourself
pip install bandit
bandit -r src/ -f html -o bandit-report.html
open bandit-report.html  # Review the results

# Or run in Docker for complete isolation
docker build -t humitron .
docker run -it humitron
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running
- At least one model pulled (e.g., `ollama pull llama3.2`)
- Node.js 20+ (for frontend development)
- Rust 1.75+ (for Tauri desktop app)

### Installation

```bash
# Clone the repository
git clone https://github.com/humitron/humitron.git
cd humitron

# Always install from the lock file
pip install -r requirements-lock.txt

# Or for development
pip install -e ".[dev]" -r requirements-lock.txt
```

### Configuration

Copy the example environment file and customize:

```bash
cp .env.example .env
# Edit .env with your settings
```

Or edit `config.yaml` directly:

```yaml
model: "llama3.2"
workspace_path: "."
max_steps: 20
temperature: 0.7
ollama_base_url: "http://localhost:11434"
log_level: "INFO"
provider: "ollama"
cloud_api_key: ""
```

Environment variables (prefixed with `HUMITRON_`) override config.yaml.

### Running Humitron

**Interactive chat mode:**
```bash
make run
# or
python -m humitron.ui.cli
```

**Single prompt:**
```bash
make run-prompt PROMPT="Read the README.md file and summarize it"
# or
python -m humitron.ui.cli "Read the README.md file and summarize it"
```

**With custom options:**
```bash
python -m humitron.ui.cli --model mistral --max-steps 10 "Your prompt"
```

**Desktop app (Tauri):**
```bash
npm run tauri:dev
```

**Docker (isolated):**
```bash
docker build -t humitron .
docker run -it humitron
```

### Development

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Security audit
make audit  # or: bandit -r src/

# Run all checks
make all

# Run benchmarks
make benchmark
```

### Project Structure

```
humitron/
├── src/
│   ├── humitron/
│   │   ├── __init__.py          # Package exports
│   │   ├── agent.py             # ReAct agent loop
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── loader.py        # Configuration loading
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── conversation.py  # Conversation memory with summarization
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py         # Agent state models
│   │   │   └── tools.py         # Tool models
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   └── planner.py       # Task planning
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── bash.py          # Bash execution
│   │   │   ├── file_ops.py      # File read/write
│   │   │   ├── registry.py      # Tool registry
│   │   │   └── web.py           # Web search
│   │   ├── ui/
│   │   │   ├── __init__.py
│   │   │   └── cli.py           # Command-line interface
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py       # Logging setup
│   │       └── safety.py        # Path/command safety
├── src-tauri/                   # Tauri desktop app
│   ├── src/
│   │   └── main.rs              # Sidecar management
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/api/                     # FastAPI backend
│   └── server.py
├── tests/                       # Unit tests
├── scripts/                     # Build/deploy scripts
├── config.yaml                  # Default configuration
├── .env.example                 # Environment variable template
├── requirements-lock.txt        # Pinned dependencies (ALWAYS install from this!)
├── requirements.txt             # Human-readable dependency list
├── pyproject.toml              # Project metadata & tool config
├── SECURITY_AUDIT.md            # Security audit results & how to audit
├── SECURITY.md                  # Security policy & vulnerability reporting
├── Dockerfile                   # Isolated container build
├── bandit-report.html           # HTML security audit report
├── bandit-report.txt            # Text security audit report
├── Makefile                     # Build automation
└── README.md                    # This file
```

### Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read a file from workspace |
| `write_file` | Write content to a file |
| `bash_execute` | Execute bash commands (sandboxed) |
| `web_search` | Search the web via DuckDuckGo |

### Cloud Providers

| Provider | Models | Setup |
|----------|--------|-------|
| **Ollama** (local) | llama3.2, mistral, phi4, codellama, etc. | `ollama pull <model>` |
| **OpenAI** | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | `OPENAI_API_KEY` |
| **Anthropic** | claude-3-5-sonnet, claude-3-opus, claude-3-haiku | `ANTHROPIC_API_KEY` |
| **OpenRouter** | 100+ models via single API | `OPENROUTER_API_KEY` |

### Safety Features

- **Path sandboxing**: All file operations restricted to workspace directory
- **Command filtering**: Dangerous commands (rm -rf /, sudo, chmod 777, etc.) are blocked
- **Token budgets**: Automatic context summarization prevents token overflow
- **Rate limiting**: Configurable request/token limits
- **Security audit**: Run `bandit -r src/` to verify yourself

### Security & Trust

- **Lock file**: `requirements-lock.txt` pins all dependency versions
- **Security audit**: `SECURITY_AUDIT.md` contains Bandit scanner results
- **No binaries**: Every file is human-readable source code
- **Docker support**: Run in complete isolation
- **Vulnerability reporting**: `SECURITY.md` explains how to report issues

### Extending Humitron

**Adding a new tool:**
1. Create `src/humitron/tools/my_tool.py`
2. Implement tool function returning `ToolResult`
3. Add to `src/humitron/tools/registry.py`
4. Re-run security audit: `bandit -r src/`

**Adding MCP servers:**
```python
from humitron.mcp.client import get_mcp_client, MCPServerConfig

client = get_mcp_client()
client.add_server(MCPServerConfig(
    name="github",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"]
))
await client.connect_server("github")
```

### Docker

```bash
# Build image
make docker-build

# Run container (isolated!)
make docker-run

# Or manually
docker build -t humitron .
docker run -it --rm humitron
```

### Building Installers

The GitHub Actions workflow builds native installers on tag push:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Produces:
- Windows: `humitron-setup.exe` (NSIS)
- macOS: `humitron.dmg` (Intel + Apple Silicon)
- Linux: `humitron.AppImage`

### License

MIT License - see [LICENSE](LICENSE) for details.

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Built by the Humitron community** | **Audit before you run** | **Trust, but verify**
