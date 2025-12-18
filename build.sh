#!/bin/bash

# ==========================================
# 🏗️  AGENT BUILDER SCRIPT
# ==========================================

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Filenames
WIN_SCRIPT="./app/windows_agent.py"
LIN_SCRIPT="./app/linux_agent.py"

# Function to print usage
usage() {
    echo -e "${YELLOW}Usage: $0 [target]${NC}"
    echo "Targets:"
    echo "  --windows   Compile the Windows Agent (.exe)"
    echo "  --linux     Compile the Linux Agent (binary)"
    echo "  --all       Compile both (Requires Wine for Windows build on Linux)"
    exit 1
}

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo -e "${RED}Error: PyInstaller is not installed.${NC}"
    echo "Run: pip install pyinstaller"
    exit 1
fi

# Function to build Windows
build_windows() {
    echo -e "\n${CYAN}>>> 🔨 Building Windows Agent...${NC}"
    
    if [ ! -f "$WIN_SCRIPT" ]; then
        echo -e "${RED}Error: $WIN_SCRIPT not found!${NC}"
        return
    fi

    # Check if running on Linux (needs Wine) or Windows
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${YELLOW}Note: Running on Linux. Attempting build via Wine...${NC}"
        # If you have wine python installed, command changes to: wine python -m PyInstaller ...
        # For standard PyInstaller on Linux, this will produce a Linux binary named 'windows_agent'
        # which is NOT what you want. 
        echo -e "${RED}⚠️  WARNING: Standard PyInstaller on Linux cannot build .exe files natively.${NC}"
        echo "   You need to run this on Windows OR use Wine with Python installed inside it."
    fi

    # The Command
    pyinstaller --onefile --uac-admin --clean "$WIN_SCRIPT"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Windows Build Complete! (Check /dist folder)${NC}"
    else
        echo -e "${RED}❌ Windows Build Failed.${NC}"
    fi
}

# Function to build Linux
build_linux() {
    echo -e "\n${CYAN}>>> 🐧 Building Linux Agent...${NC}"
    
    if [ ! -f "$LIN_SCRIPT" ]; then
        echo -e "${RED}Error: $LIN_SCRIPT not found!${NC}"
        return
    fi

    # The Command
    pyinstaller --onefile --clean "$LIN_SCRIPT"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Linux Build Complete! (Check /dist folder)${NC}"
    else
        echo -e "${RED}❌ Linux Build Failed.${NC}"
    fi
}

# Parse Parameters
if [ $# -eq 0 ]; then
    usage
fi

case "$1" in
    --windows)
        build_windows
        ;;
    --linux)
        build_linux
        ;;
    --all)
        build_linux
        build_windows
        ;;
    *)
        echo -e "${RED}Invalid option: $1${NC}"
        usage
        ;;
esac