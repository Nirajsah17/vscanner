#!/bin/bash

# ==========================================
# 🏗️  MODULAR AGENT BUILDER
# ==========================================

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
# Point this to your new entry file
ENTRY_POINT="./app/main.py"
OUTPUT_NAME="vscanner_agent"
DIST_DIR="./dist"

# Check PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${RED}Error: PyInstaller not found.${NC}"
    echo "Run: pip install pyinstaller"
    exit 1
fi

# Function to clean previous builds (Important for modular builds)
clean_build() {
    echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
    rm -rf build/ dist/ *.spec
}

# ==========================================
# 🐧 BUILD FOR LINUX
# ==========================================
build_linux() {
    echo -e "\n${CYAN}>>> 🐧 Building Linux Binary...${NC}"
    
    # Check if we are actually on Linux
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        echo -e "${RED}Error: You are not on Linux. Cannot build Linux binary here.${NC}"
        return
    fi

    clean_build

    # --paths: Tells PyInstaller where to look for modules
    # --hidden-import: Ensures dynamic imports aren't missed (optional but safe)
    pyinstaller --onefile \
        --clean \
        --name "${OUTPUT_NAME}_linux" \
        --paths="./app/v2" \
        "$ENTRY_POINT"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Success! Binary is at: $DIST_DIR/${OUTPUT_NAME}_linux${NC}"
        # Set permission just in case
        chmod +x "$DIST_DIR/${OUTPUT_NAME}_linux"
    else
        echo -e "${RED}❌ Build Failed.${NC}"
    fi
}

# ==========================================
# 🪟 BUILD FOR WINDOWS
# ==========================================
build_windows() {
    echo -e "\n${CYAN}>>> 🔨 Building Windows Executable...${NC}"

    # CRITICAL CHECK: Are we on Windows?
    # MINGW/CYGWIN/MSYS usually indicate Git Bash on Windows
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "cygwin" && "$OSTYPE" != "win32" ]]; then
        echo -e "${RED}⚠️  CRITICAL WARNING: You are running on Linux/Mac.${NC}"
        echo -e "   Standard PyInstaller CANNOT build .exe files on Linux."
        echo -e "   You must run this script on a Windows machine (Git Bash or WSL)."
        echo -e "   Skipping build..."
        return
    fi

    clean_build

    pyinstaller --onefile \
        --clean \
        --uac-admin \
        --name "${OUTPUT_NAME}_windows" \
        --paths="./vscanner_agent" \
        "$ENTRY_POINT"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Success! Executable is at: $DIST_DIR/${OUTPUT_NAME}_windows.exe${NC}"
    else
        echo -e "${RED}❌ Build Failed.${NC}"
    fi
}

# ==========================================
# MAIN LOGIC
# ==========================================

if [ ! -f "$ENTRY_POINT" ]; then
    echo -e "${RED}Error: Entry point '$ENTRY_POINT' not found!${NC}"
    echo "Make sure you are in the root directory and 'vscanner_agent/main.py' exists."
    exit 1
fi

case "$1" in
    --linux)
        build_linux
        ;;
    --windows)
        build_windows
        ;;
    *)
        echo -e "${YELLOW}Usage: $0 [--linux | --windows]${NC}"
        echo "Note: Run --linux on a Linux machine, and --windows on a Windows machine."
        ;;
esac