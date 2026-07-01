# AI Rules for Humitron

This file defines the tech stack and library usage rules for AI-assisted development on this project.

---

## Tech Stack

- **Core Language**: Python 3.10+ for backend agent logic, tool implementations, and cloud API
- **Local Model Runtime**: Ollama for running LLMs locally (llama3.2, mistral, etc.)
- **Web Framework**: FastAPI for cloud backend REST API
- **Frontend**: TypeScript + Electron/Tauri for desktop application
- **Package Management**: pip (Python), npm (Node.js)
- **Testing**: pytest for Python, Vitest/Jest for TypeScript
- **Code Quality**: Black (Python formatter), ESLint + Prettier (TypeScript)
- **Containerization**: Docker for sandboxing and cloud deployment
- **Version Control**: Git with conventional commits
- **CI/CD**: GitHub Actions for testing and releases

---

## Library Usage Rules

### Python (Backend / Agent Core)

| Category | Approved Libraries | Notes |
|----------|-------------------|-------|
| **HTTP Client** | `httpx`, `requests` | Prefer `httpx` for async support |
| **Async/Concurrency** | `asyncio`, `anyio` | Use `asyncio` as standard |
| **CLI/Argument Parsing** | `typer`, `click` | `typer` preferred for new CLIs |
| **Configuration** | `pydantic-settings`, `python-dotenv` | Pydantic v2 for validation |
| **Logging** | `loguru`, `structlog` | `loguru` for simplicity |
| **Serialization** | `pydantic`, `msgspec` | Pydantic v2 for models/schemas |
| **File I/O** | `pathlib`, `aiofiles` | Use `pathlib` (stdlib) first |
| **Subprocess/Shell** | `subprocess` (stdlib), `sh` | Prefer stdlib; `sh` only if needed |
| **Testing** | `pytest`, `pytest-asyncio`, `pytest-mock` | Standard test stack |
| **Type Checking** | `mypy`, `pyright` | Run in CI |
| **Formatting/Linting** | `black`, `ruff` | Ruff replaces flake8/isort |
| **Database (if needed)** | `sqlalchemy`, `sqlite3` (stdlib) | SQLite for local; Postgres for cloud |
| **Observability** | `opentelemetry`, `prometheus-client` | Optional, for cloud mode |

**Forbidden**: `urllib` (use httpx), `threading` for async work (use asyncio), `pickle` for untrusted data.

---

### TypeScript / JavaScript (Frontend / Desktop)

| Category | Approved Libraries | Notes |
|----------|-------------------|-------|
| **UI Framework** | React (if Electron), SolidJS (if Tauri) | Follow existing choice |
| **State Management** | `zustand`, `jotai`, React Context | Keep simple; avoid Redux |
| **Routing** | `react-router` (React), `@solidjs/router` (Solid) | |
| **Styling** | Tailwind CSS, CSS Modules | Tailwind preferred |
| **Component Library** | shadcn/ui (Radix-based), lucide-react (icons) | Already installed |
| **Forms** | `react-hook-form` + `zod` | Zod for validation |
| **HTTP Client** | `axios`, `ky`, or fetch (stdlib) | `ky` preferred for simplicity |
| **Testing** | `vitest`, `@testing-library/react` | Vitest over Jest |
| **Type Checking** | `typescript` (strict mode) | Strict: true in tsconfig |
| **Formatting/Linting** | `eslint`, `prettier`, `@typescript-eslint` | Airbnb base config |
| **Build/Bundler** | `vite`, `electron-builder` / `tauri-cli` | Vite for dev; platform tool for build |
| **IPC (Electron)** | `electron` (contextBridge, ipcRenderer) | Secure IPC only |
| **System APIs (Tauri)** | `@tauri-apps/api` | If using Tauri |

**Forbidden**: `moment.js` (use `date-fns` or `dayjs`), `classnames` (use `clsx` or template literals), large UI kits (MUI, AntD) — keep bundle small.

---

### Cross-Cutting Rules

1. **No new dependencies without approval** — Add a comment in PR explaining why it's needed.
2. **Prefer stdlib first** — Only add a package if stdlib is genuinely insufficient.
3. **Pin versions** — Use exact versions in `requirements.txt` / `package.json` (no `^` or `~`).
4. **Security first** — Audit new deps with `pip-audit` / `npm audit` before merging.
5. **Local-first** — All features must work offline with Ollama; cloud is optional burst.
6. **Privacy by default** — Never log user prompts, code, or file contents to external services.
7. **Type everything** — Python: type hints on all public functions. TypeScript: strict mode, no `any`.
8. **Test coverage** — New code requires tests. Target ≥80% coverage on changed files.
9. **Document public APIs** — Docstrings (Python) / JSDoc (TS) for all exported functions.
10. **Conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

---

## Project Structure Conventions

```
humitron/
├── backend/           # Python FastAPI + agent core
│   ├── agent/         # ReAct loop, planning, memory
│   ├── tools/         # Tool implementations (file, bash, web, etc.)
│   ├── api/           # FastAPI routes
│   ├── models/        # Pydantic schemas
│   └── tests/
├── frontend/          # TypeScript desktop app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   └── tests/
├── docker/            # Dockerfiles for sandbox/cloud
├── .github/workflows/ # CI/CD
└── docs/              # Markdown documentation
```

---

## AI Assistant Instructions

When contributing code:
- Follow the style guides in `CONTRIBUTING.md` (PEP 8 + Black for Python; Airbnb + Prettier for TS)
- Write tests before or alongside implementation
- Update relevant documentation
- Keep changes focused and atomic
- Explain non-obvious logic in comments
- Never commit secrets, API keys, or `.env` files