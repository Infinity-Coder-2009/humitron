


```markdown
# Contributing to Humitron

First off, thank you for considering contributing to Humitron! 

We're building a local-first, hybrid AI agent that puts privacy and control back in users' hands. Whether you're fixing a bug, adding a feature, or improving documentation—every contribution matters.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Community](#community)

---

##  Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and harassment-free experience for everyone, regardless of age, background, or experience level.

**In short:** Be kind, be respectful, and assume good intentions.

---

##  How Can I Contribute?

### 1.  Report Bugs

If you find a bug, please [open an issue](https://github.com/humitron/humitron/issues) and include:

- A clear title and description
- Steps to reproduce the bug
- Expected vs actual behavior
- Screenshots or logs (if applicable)
- Your OS and Humitron version

### 2.  Suggest Features

We love new ideas! Open an issue with:

- A clear description of the feature
- Why it's valuable to users
- Any potential implementation notes

### 3.  Improve Documentation

Good docs are essential. You can help by:

- Fixing typos or unclear sections
- Adding usage examples
- Translating docs into your language
- Writing tutorials or blog posts

### 4.  Write Code

We accept code contributions in these areas:

| Area | Stack | Difficulty |
|------|-------|------------|
| **Core Agent Loop** | Python, ReAct pattern | 🟡 Medium |
| **Tool Implementations** | Python (file I/O, bash, web) | 🟢 Easy |
| **Desktop UI** | TypeScript, Electron/Tauri | 🔴 Hard |
| **Cloud Backend** | Python, FastAPI, Docker | 🔴 Hard |
| **Testing** | Python (pytest) | 🟢 Easy |
| **Documentation** | Markdown | 🟢 Very Easy |

---

##  Development Setup

### Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| [Python](https://www.python.org/) | 3.10+ | Core agent logic |
| [Node.js](https://nodejs.org/) | 18+ | UI (if using Electron) |
| [Ollama](https://ollama.ai/) | Latest | Local model runner |
| [Git](https://git-scm.com/) | Any | Version control |
| [Docker](https://www.docker.com/) (optional) | Latest | Sandboxing and cloud testing |

### Quick Start

1. **Fork the repo**

```bash
git clone https://github.com/your-username/humitron.git
cd humitron
```

2. **Set up the backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set up the frontend (if applicable)**

```bash
cd ../frontend
npm install
```

4. **Run the app locally**

```bash
# Backend
cd backend
python main.py

# Frontend (in another terminal)
cd frontend
npm run dev
```

5. **Run tests**

```bash
cd backend
pytest tests/
```

---

##  Pull Request Process

We follow a simple PR workflow:

1. **Find an issue** to work on, or create one.
2. **Assign yourself** to the issue (so others know you're working on it).
3. **Create a branch** with a descriptive name:
   ```bash
   git checkout -b feat/add-web-search-tool
   ```
4. **Write your code** with tests.
5. **Update documentation** if you changed functionality.
6. **Run tests locally** to make sure everything passes.
7. **Push your branch** and open a Pull Request.
8. **Link your PR to the issue** (e.g., `Closes #123`).

### PR Checklist

- [ ] My code follows the style guidelines
- [ ] I have added tests that prove my fix/feature works
- [ ] I have updated the documentation
- [ ] All tests pass locally
- [ ] I have added a changelog entry (if applicable)

---

##  Style Guidelines

### Python

We follow [PEP 8](https://peps.python.org/pep-0008/) with these additions:

- Use **4 spaces** (not tabs)
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Max line length: **88 characters** (Black default)
- Add docstrings for all public functions

**Example:**

```python
def execute_bash_command(command: str, timeout: int = 30) -> dict:
    """
    Execute a bash command and return the result.
    
    Args:
        command: The bash command to execute.
        timeout: Maximum execution time in seconds.
    
    Returns:
        A dict with 'output', 'error', and 'exit_code' keys.
    
    Raises:
        TimeoutError: If the command exceeds timeout.
    """
    pass
```

### TypeScript / JavaScript

We follow the [Airbnb Style Guide](https://github.com/airbnb/javascript) with these additions:

- Use **2 spaces** for indentation
- Use **camelCase** for variables and functions
- Use **PascalCase** for components and classes
- Use **semicolons**
- Use **arrow functions** over `function` keyword

**Example:**

```typescript
interface AgentMessage {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
}

const sendMessage = async (message: AgentMessage): Promise<AgentResponse> => {
  // Implementation
};
```

---

##  Issue Labels

We use these labels to help contributors find the right tasks:

| Label | Meaning |
|-------|---------|
| `good-first-issue` | Perfect for first-time contributors |
| `help-wanted` | We'd love help on this |
| `bug` | Something is broken |
| `enhancement` | New feature or improvement |
| `documentation` | Docs need work |
| `question` | We need more info |


---

##  For "Vibe Coders" (AI-Assisted Contributors)

We welcome contributions written with AI assistance! Here's how to do it well:

1. **Acknowledge AI use** in your PR description (e.g., "This PR was written with the help of Claude/Cursor").
2. **Review all AI-generated code** carefully before submitting.
3. **Test your changes** thoroughly—AI doesn't understand your specific setup.
4. **Explain the logic** in comments—the next person (human or AI) will thank you.

**Why this matters:** We believe "vibe coding" is the future. We want Humitron to be a project where AI-assisted contributors feel welcome, not judged.

---

##  Thank You!

Every contribution, no matter how small, makes Humitron better. You are part of this project's story.

**Now go build something amazing!** 🚀

---

*Humitron is built by a solo developer—and contributors like you are the reason it will succeed.*
```
