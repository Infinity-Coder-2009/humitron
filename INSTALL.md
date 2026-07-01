# Humitron Installation Guide

## Quick Install (Recommended)

### Windows
1. Download `humitron-setup.exe` from [Releases](https://github.com/humitron/humitron/releases/latest)
2. Run the installer
3. Follow the setup wizard
4. Launch Humitron from Start Menu

### macOS
1. Download `humitron.dmg` (Intel) or `humitron-arm64.dmg` (Apple Silicon) from [Releases](https://github.com/humitron/humitron/releases/latest)
2. Open the DMG file
3. Drag Humitron to Applications folder
4. Launch from Applications or Spotlight

### Linux
1. Download `humitron.AppImage` from [Releases](https://github.com/humitron/humitron/releases/latest)
2. Make it executable: `chmod +x humitron.AppImage`
3. Run: `./humitron.AppImage`

## First Run Setup

When you launch Humitron for the first time, you'll see a welcome screen that guides you through:

1. **Install Ollama** - The local AI runtime (free, private)
2. **Pull a Model** - Download Llama 3.2 or another model
3. **Choose Workspace** - Select a folder for file operations
4. **Start Backend** - The Python agent starts automatically

## Manual Prerequisites (Optional)

If you prefer to set up manually before installing:

### Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download/windows
```

### Pull a Model
```bash
ollama pull llama3.2
```

### Verify Installation
```bash
ollama list
# Should show llama3.2 or your chosen model
```

## Configuration

### Settings Panel
Access via the gear icon in the sidebar:
- **Model**: Switch between local (Ollama) and cloud models
- **Temperature**: Control creativity (0.0-2.0)
- **Max Steps**: Limit agent reasoning steps
- **Workspace**: Folder for file read/write operations
- **API Keys**: Add cloud provider keys (OpenAI, Anthropic, OpenRouter)

### Config File Locations
- **Windows**: `%APPDATA%\Humitron\config.json`
- **macOS**: `~/Library/Application Support/Humitron/config.json`
- **Linux**: `~/.config/humitron/config.json`

## Troubleshooting

### "Ollama not running"
- Make sure Ollama is installed and running: `ollama serve`
- Check if port 11434 is available

### "Model not found"
- Pull a model: `ollama pull llama3.2`
- Or use the "Pull Model" button in settings

### "Backend failed to start"
- Check if Python 3.10+ is installed
- Try running from terminal to see error messages
- Check antivirus/firewall isn't blocking the sidecar

### App won't launch (Linux)
```bash
# Make sure AppImage is executable
chmod +x humitron.AppImage

# If FUSE issue:
sudo apt-get install fuse libfuse2
# Or run with:
./humitron.AppImage --no-sandbox
```

### macOS "App is damaged"
```bash
# Remove quarantine attribute
xattr -cr /Applications/Humitron.app
```

## Uninstalling

### Windows
- Use "Add or Remove Programs" in Settings
- Or run uninstaller from Start Menu

### macOS
- Drag Humitron.app to Trash
- Remove config: `rm -rf ~/Library/Application\ Support/Humitron`

### Linux
- Delete the AppImage file
- Remove config: `rm -rf ~/.config/humitron`

## Support

- **Issues**: [GitHub Issues](https://github.com/humitron/humitron/issues)
- **Discussions**: [GitHub Discussions](https://github.com/humitron/humitron/discussions)
- **Documentation**: [docs.humitron.dev](https://docs.humitron.dev)