#!/bin/bash

# Configuration Variables
APP_NAME="vscanner"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
# Using 'raw' URL for direct binary download
BINARY_URL="https://github.com/Nirajsah17/vscanner/raw/develope/dist/linux_agent"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for Root Privileges
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root.${NC}"
   echo "Try running: sudo ./manager.sh [install|install-local|update|uninstall|status]"
   exit 1
fi

# ==========================================
# HELPER: CONFIGURE SYSTEMD
# ==========================================
# This function handles the common setup steps (permissions, service file, starting)
configure_service() {
    # 1. Set Permissions
    echo "Setting executable permissions..."
    chmod +x "$INSTALL_DIR/$APP_NAME"

    # 2. Create Service File
    echo "Creating systemd service file..."
    cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=VScanner Service
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/$APP_NAME
Restart=always
RestartSec=5
Environment="PYTHONUNBUFFERED=1"
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=$APP_NAME

[Install]
WantedBy=multi-user.target
EOF

    # 3. Enable and Start
    echo "Reloading systemd and starting service..."
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    systemctl restart "$APP_NAME"

    # 4. Verification
    if systemctl is-active --quiet "$APP_NAME"; then
        echo -e "${GREEN}Success! $APP_NAME is installed and running.${NC}"
        echo "View logs with: journalctl -u $APP_NAME -f"
    else
        echo -e "${RED}Warning: Service installed but failed to start.${NC}"
        echo "Check status: systemctl status $APP_NAME"
    fi
}

# ==========================================
# INSTALL FROM GITHUB (REMOTE)
# ==========================================
install_app() {
    echo -e "${YELLOW}Starting installation for $APP_NAME (from GitHub)...${NC}"

    # 1. Check for Curl
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: 'curl' is not installed.${NC}"
        echo "Please install it (e.g., sudo apt install curl) and try again."
        exit 1
    fi

    # 2. Stop service if running
    if systemctl is-active --quiet "$APP_NAME"; then
        echo "Stopping existing service..."
        systemctl stop "$APP_NAME"
    fi

    # 3. Create Directory
    if [[ ! -d "$INSTALL_DIR" ]]; then
        echo "Creating directory $INSTALL_DIR..."
        mkdir -p "$INSTALL_DIR"
    fi

    # 4. Download Binary
    echo "Downloading binary from GitHub..."
    curl -L -o "$INSTALL_DIR/$APP_NAME" "$BINARY_URL"

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Error: Download failed. Check internet or URL.${NC}"
        exit 1
    fi

    # 5. Configure and Start
    configure_service
}

# ==========================================
# INSTALL FROM LOCAL FILE
# ==========================================
install_local_app() {
    LOCAL_FILE="$1"
    
    echo -e "${YELLOW}Starting installation for $APP_NAME (from Local File)...${NC}"

    # 1. Validate Input
    if [[ -z "$LOCAL_FILE" ]]; then
        echo -e "${RED}Error: No file path provided.${NC}"
        echo "Usage: sudo ./manager.sh install-local /path/to/your/binary"
        exit 1
    fi

    if [[ ! -f "$LOCAL_FILE" ]]; then
        echo -e "${RED}Error: File '$LOCAL_FILE' not found.${NC}"
        exit 1
    fi

    # 2. Stop service if running
    if systemctl is-active --quiet "$APP_NAME"; then
        echo "Stopping existing service..."
        systemctl stop "$APP_NAME"
    fi

    # 3. Create Directory
    if [[ ! -d "$INSTALL_DIR" ]]; then
        echo "Creating directory $INSTALL_DIR..."
        mkdir -p "$INSTALL_DIR"
    fi

    # 4. Copy Binary
    echo "Copying binary from $LOCAL_FILE..."
    cp "$LOCAL_FILE" "$INSTALL_DIR/$APP_NAME"

    # 5. Configure and Start
    configure_service
}

# ==========================================
# UPDATE (REMOTE)
# ==========================================
update_app() {
    echo -e "${YELLOW}Updating $APP_NAME...${NC}"

    if [[ ! -d "$INSTALL_DIR" ]]; then
        echo -e "${RED}Error: Directory $INSTALL_DIR does not exist.${NC}"
        echo "Please run './manager.sh install' first."
        exit 1
    fi

    echo "Stopping service..."
    systemctl stop "$APP_NAME"

    echo "Downloading latest binary..."
    curl -L -o "$INSTALL_DIR/$APP_NAME" "$BINARY_URL"

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Error: Download failed. Aborting update.${NC}"
        systemctl start "$APP_NAME"
        exit 1
    fi

    chmod +x "$INSTALL_DIR/$APP_NAME"
    
    echo "Restarting service..."
    systemctl start "$APP_NAME"

    if systemctl is-active --quiet "$APP_NAME"; then
        echo -e "${GREEN}Success! $APP_NAME has been updated.${NC}"
    else
        echo -e "${RED}Error: Updated service failed to start.${NC}"
        systemctl status "$APP_NAME" --no-pager
    fi
}

# ==========================================
# UNINSTALL FUNCTION
# ==========================================
uninstall_app() {
    echo -e "${YELLOW}Starting uninstallation for $APP_NAME...${NC}"

    if systemctl list-unit-files | grep -q "$APP_NAME.service"; then
        echo "Stopping and disabling service..."
        systemctl stop "$APP_NAME"
        systemctl disable "$APP_NAME"
    else
        echo "Service not found in systemd. Skipping stop."
    fi

    if [[ -f "$SERVICE_FILE" ]]; then
        echo "Removing service file..."
        rm "$SERVICE_FILE"
        systemctl daemon-reload
    fi

    if [[ -d "$INSTALL_DIR" ]]; then
        echo "Removing installation files..."
        rm -rf "$INSTALL_DIR"
    fi

    echo -e "${GREEN}Success! $APP_NAME has been uninstalled.${NC}"
}

# ==========================================
# STATUS FUNCTION
# ==========================================
status_app() {
    echo -e "${BLUE}Checking status for $APP_NAME...${NC}"
    
    if [[ ! -f "$SERVICE_FILE" ]]; then
        echo -e "${RED}Service is not installed.${NC}"
        return
    fi

    systemctl status "$APP_NAME" --no-pager
}

# ==========================================
# MAIN EXECUTION
# ==========================================
case "$1" in
    install)
        install_app
        ;;
    install-local)
        # Pass the second argument (the file path) to the function
        install_local_app "$2"
        ;;
    update)
        update_app
        ;;
    uninstall)
        uninstall_app
        ;;
    status)
        status_app
        ;;
    *)
        echo "Usage: sudo ./manager.sh {install|install-local <path>|update|uninstall|status}"
        exit 1
        ;;
esac