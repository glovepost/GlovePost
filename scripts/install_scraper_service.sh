#!/bin/bash

# This script installs the GlovePost content scraper as a systemd service

# Exit on error
set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up GlovePost Content Scraper Service..."
echo "Base directory: $BASE_DIR"

# Ensure we have the necessary permissions
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to run with sudo privileges to install the systemd service."
    echo "Please run: sudo $0"
    exit 1
fi

# Make sure refresh_content.py is executable
chmod +x "$SCRIPT_DIR/refresh_content.py"

# Create a proper systemd service file
SERVICE_FILE="$SCRIPT_DIR/glovepost-scraper.service"

# Replace user in service file with the current user
CURRENT_USER=$(logname || echo "$SUDO_USER" || echo "$USER")
sed -i "s/User=mythos/User=$CURRENT_USER/g" "$SERVICE_FILE"

# Update paths in service file
BASE_DIR_ESCAPED=$(echo "$BASE_DIR" | sed 's/\//\\\//g')
sed -i "s/\/home\/mythos\/glovepostsite\/GlovePost/$BASE_DIR_ESCAPED/g" "$SERVICE_FILE"

# Install the service
echo "Installing systemd service..."
cp "$SERVICE_FILE" /etc/systemd/system/glovepost-scraper.service

# Reload systemd
systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting service..."
systemctl enable glovepost-scraper.service
systemctl start glovepost-scraper.service

# Display service status
echo "Service installed successfully!"
echo "Service status:"
systemctl status glovepost-scraper.service

echo ""
echo "You can control the service with these commands:"
echo "  systemctl start glovepost-scraper.service    # Start the service"
echo "  systemctl stop glovepost-scraper.service     # Stop the service"
echo "  systemctl restart glovepost-scraper.service  # Restart the service"
echo "  systemctl status glovepost-scraper.service   # Check service status"
echo "  journalctl -u glovepost-scraper.service      # View service logs"
echo ""
echo "The scraper will run every hour, scraping content from all configured sources"
echo "To adjust settings, edit /etc/systemd/system/glovepost-scraper.service and restart the service"