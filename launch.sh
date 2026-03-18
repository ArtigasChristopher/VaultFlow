#!/bin/bash
# VaultFlow Launch Script (Linux/WSL)
# This script starts the backend and n8n using Docker, then opens the frontend in Chrome.

# Check for Docker permissions
if ! docker info > /dev/null 2>&1; then
    echo -e "\033[0;31mError: Docker permission denied.\033[0m"
    echo -e "Please try running with \033[0;33msudo ./launch.sh\033[0m or add your user to the 'docker' group."
    exit 1
fi

echo -e "\033[0;36mStarting VaultFlow services with Docker Compose...\033[0m"

# Start Docker containers
docker compose up -d

echo -e "\033[0;33mWaiting for services to start...\033[0m"
sleep 5

# Check if containers are running
containers=$(docker ps --filter "name=vaultflow" --format "{{.Names}}")
count=$(echo "$containers" | wc -l)
if [ "$count" -lt 2 ]; then
    echo -e "\033[0;31mWarning: Some containers might not be running correctly. Check 'docker ps'.\033[0m"
fi

echo -e "\033[0;32mOpening Frontend in Chrome...\033[0m"

# Get the absolute path to index.html (WSL path)
FRONTEND_PATH=$(realpath ./frontend/index.html)

# Check if we are running under WSL
if [ -n "$IS_WSL" ] || grep -qi microsoft /proc/version || command -v wslpath > /dev/null; then
    echo -e "\033[0;33mWSL Detected: Opening on Windows...\033[0m"
    # Convert WSL path to Windows path
    WIN_PATH=$(wslpath -w "$FRONTEND_PATH")
    # Use 'cmd.exe /c start' which is often more reliable than explorer.exe for URLs/files
    cmd.exe /c start "" "$WIN_PATH"
else
    # Native Linux
    xdg-open "$FRONTEND_PATH" || echo "Please open $FRONTEND_PATH in your browser."
fi

echo -e "\033[0;32mVaultFlow is ready!\033[0m"
echo "Backend: http://localhost:8000"
echo "n8n: http://localhost:5678"
