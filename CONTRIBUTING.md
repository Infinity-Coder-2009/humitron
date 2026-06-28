# Contributing to Humitron

First off, thank you for considering contributing to Humitron! 

We're building a local-first, hybrid AI agent that puts privacy and control back in users' hands. Whether you're fixing a bug, adding a feature, or improving documentation—every contribution matters.

##  Table of Contents

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
| **Core Agent Loop** | Python, ReAct pattern |  Medium |
| **Tool Implementations** | Python (file I/O, bash, web) |  Easy |
| **Desktop UI** | TypeScript, Electron/Tauri |  Hard |
| **Cloud Backend** | Python, FastAPI, Docker |  Hard |
| **Testing** | Python (pytest) | Easy |
| **Documentation** | Markdown |  Very Easy |

---

## 🛠️ Development Setup

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
