#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}mux setup script${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================================
# 1. Check Python version
# ============================================================
echo -e "${BLUE}[1/6] Checking Python version...${NC}"
PYTHON_CMD=$(command -v python3 || command -v python || true)

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo -e "${RED}✗ Python $PYTHON_VERSION detected. Need Python 3.10+${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
echo

# ============================================================
# 2. Create venv and install dependencies
# ============================================================
echo -e "${BLUE}[2/6] Setting up Python virtual environment...${NC}"

if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo -e "${GREEN}✓ Created .venv${NC}"
else
    echo -e "${GREEN}✓ .venv already exists${NC}"
fi

# Activate venv
source .venv/bin/activate

echo -e "${BLUE}Installing dependencies...${NC}"
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

# ============================================================
# 3. Create logs directory
# ============================================================
echo -e "${BLUE}[3/6] Setting up directories...${NC}"
mkdir -p logs
echo -e "${GREEN}✓ Created logs directory${NC}"
echo

# ============================================================
# 4. Detect installed CLIs
# ============================================================
echo -e "${BLUE}[4/6] Detecting installed CLI tools...${NC}"

CLAUDE_FOUND=0
CODEX_FOUND=0
GEMINI_FOUND=0

if command -v claude &> /dev/null; then
    CLAUDE_FOUND=1
    echo -e "${GREEN}✓ claude found${NC}"
else
    echo -e "${YELLOW}○ claude not found${NC}"
fi

if command -v codex &> /dev/null; then
    CODEX_FOUND=1
    echo -e "${GREEN}✓ codex found${NC}"
else
    echo -e "${YELLOW}○ codex not found${NC}"
fi

if command -v gemini &> /dev/null; then
    GEMINI_FOUND=1
    echo -e "${GREEN}✓ gemini found${NC}"
else
    echo -e "${YELLOW}○ gemini not found${NC}"
fi

if [ $CLAUDE_FOUND -eq 0 ] && [ $CODEX_FOUND -eq 0 ] && [ $GEMINI_FOUND -eq 0 ]; then
    echo -e "${YELLOW}⚠ No CLI tools found. Install claude, codex, or gemini to use mux with those tools.${NC}"
else
    echo -e "${GREEN}✓ At least one CLI tool found${NC}"
fi
echo

# ============================================================
# 5. Configure MCP servers
# ============================================================
echo -e "${BLUE}[5/6] Configuring MCP servers...${NC}"

# Get absolute path to mux directory
MUX_PATH="$SCRIPT_DIR"
VENV_PYTHON="$MUX_PATH/.venv/bin/python3"

# Function to configure Claude
configure_claude() {
    CLAUDE_CONFIG="$HOME/.claude/settings.json"

    if [ ! -f "$CLAUDE_CONFIG" ]; then
        echo -e "${YELLOW}  Creating $CLAUDE_CONFIG${NC}"
        mkdir -p "$HOME/.claude"
        echo '{}' > "$CLAUDE_CONFIG"
    fi

    # Use Python to safely merge JSON
    $PYTHON_CMD << 'PYEOF'
import json
import sys
import os

config_path = os.path.expanduser("~/.claude/settings.json")
mux_path = sys.argv[1]
venv_python = sys.argv[2]

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['mux'] = {
    'command': venv_python,
    'args': ['-m', 'mux.mcp_server'],
    'cwd': mux_path
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

sys.exit(0)
PYEOF
}

# Function to configure Codex
configure_codex() {
    # Use codex CLI to add MCP server
    codex mcp add mux -- "$VENV_PYTHON" -m mux.mcp_server 2>/dev/null || true

    # Enable it in config.toml if not already
    CODEX_CONFIG="$HOME/.codex/config.toml"
    if [ -f "$CODEX_CONFIG" ]; then
        # Check if mux is already in config
        if grep -q "^\[mcp_servers\.mux\]" "$CODEX_CONFIG"; then
            # Already configured, just ensure enabled = true
            sed -i.bak '/^\[mcp_servers\.mux\]/,/^\[/ { /enabled = false/s/false/true/ }' "$CODEX_CONFIG"
            rm -f "$CODEX_CONFIG.bak"
        fi
    fi
}

# Function to configure Gemini
configure_gemini() {
    # Use gemini CLI to add MCP server
    gemini mcp add mux "$VENV_PYTHON -m mux.mcp_server" 2>/dev/null || true
}

# Configure each found CLI
if [ $CLAUDE_FOUND -eq 1 ]; then
    configure_claude "$MUX_PATH" "$VENV_PYTHON"
    echo -e "${GREEN}✓ Configured Claude${NC}"
fi

if [ $CODEX_FOUND -eq 1 ]; then
    configure_codex
    echo -e "${GREEN}✓ Configured Codex${NC}"
fi

if [ $GEMINI_FOUND -eq 1 ]; then
    configure_gemini
    echo -e "${GREEN}✓ Configured Gemini${NC}"
fi

echo

# ============================================================
# 6. Run doctor to verify
# ============================================================
echo -e "${BLUE}[6/6] Verifying installation...${NC}"

if python3 -m mux.cli doctor > /dev/null 2>&1; then
    echo -e "${GREEN}✓ System check passed${NC}"
else
    echo -e "${YELLOW}⚠ System check reported issues (see below)${NC}"
    python3 -m mux.cli doctor || true
fi
echo

# ============================================================
# Summary
# ============================================================
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo

echo -e "${BLUE}Configured CLIs:${NC}"
if [ $CLAUDE_FOUND -eq 1 ]; then
    echo -e "  ${GREEN}✓${NC} Claude Code"
fi
if [ $CODEX_FOUND -eq 1 ]; then
    echo -e "  ${GREEN}✓${NC} Codex"
fi
if [ $GEMINI_FOUND -eq 1 ]; then
    echo -e "  ${GREEN}✓${NC} Gemini"
fi

if [ $CLAUDE_FOUND -eq 0 ] && [ $CODEX_FOUND -eq 0 ] && [ $GEMINI_FOUND -eq 0 ]; then
    echo -e "  ${YELLOW}○${NC} (None installed)"
fi

echo

echo -e "${BLUE}Next steps:${NC}"
echo

if [ $CLAUDE_FOUND -eq 1 ]; then
    echo "1. ${YELLOW}Restart Claude Code${NC}"
    echo "   Then use: @mux \"<task>\""
    echo
fi

if [ $CODEX_FOUND -eq 1 ]; then
    echo "1. ${YELLOW}Restart Codex${NC}"
    echo "   Then use: codex <task>"
    echo
fi

if [ $GEMINI_FOUND -eq 1 ]; then
    echo "1. ${YELLOW}Restart Gemini${NC}"
    echo "   Then use: gemini <task>"
    echo
fi

echo -e "${BLUE}Quick test (CLI):${NC}"
echo "  python3 -m mux.cli run --task \"Create /tmp/mux-test file\""
echo

echo -e "${BLUE}Check status:${NC}"
echo "  python3 -m mux.cli status"
echo

echo -e "${BLUE}Set up a local model (optional but recommended):${NC}"
echo "  ${YELLOW}Ollama${NC} (simplest): https://ollama.ai"
echo "    ollama run mistral:7b"
echo "  ${YELLOW}LM Studio${NC} (GUI): https://lmstudio.ai"
echo "  ${YELLOW}Qwen 35B${NC} (advanced): See docs/qwen-35b-setup.md"
echo

echo -e "${GREEN}Done! Enjoy mux.${NC}"
