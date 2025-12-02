#!/bin/bash
# Script to fix Docker Compose 'ContainerConfig' KeyError
# This error occurs with docker-compose v1.29.2 and newer Docker Engine
# The permanent solution is to upgrade to Docker Compose V2

set -e

echo "🔧 Fixing Docker Compose compatibility issue..."
echo ""

# Step 1: Check current docker-compose version
echo "📋 Current docker-compose version:"
docker-compose --version 2>/dev/null || echo "docker-compose not found"
docker compose version 2>/dev/null || echo "docker compose (V2) not found"
echo ""

# Step 2: Stop all containers first to avoid conflicts
echo "⏹️ Stopping all containers..."
docker-compose down 2>/dev/null || true
docker compose down 2>/dev/null || true
echo ""

# Step 3: Remove old docker-compose if it exists
echo "🗑️ Removing old docker-compose (v1)..."
if [ -f /usr/bin/docker-compose ]; then
    sudo rm -f /usr/bin/docker-compose
    echo "   Removed /usr/bin/docker-compose"
fi
if [ -f /usr/local/bin/docker-compose ]; then
    sudo rm -f /usr/local/bin/docker-compose
    echo "   Removed /usr/local/bin/docker-compose"
fi
echo ""

# Step 4: Install Docker Compose V2 plugin
echo "📦 Installing Docker Compose V2 plugin..."
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins

# Get latest version
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
echo "   Latest version: $COMPOSE_VERSION"

# Download for Linux x86_64
curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

# Also install system-wide
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
echo ""

# Step 5: Create compatibility alias
echo "🔗 Creating compatibility alias..."
echo 'alias docker-compose="docker compose"' >> ~/.bashrc
echo 'alias docker-compose="docker compose"' >> ~/.zshrc 2>/dev/null || true

# Create a wrapper script for scripts that call docker-compose directly
sudo tee /usr/local/bin/docker-compose > /dev/null << 'EOF'
#!/bin/bash
docker compose "$@"
EOF
sudo chmod +x /usr/local/bin/docker-compose
echo ""

# Step 6: Clean up old containers with the problematic config
echo "🧹 Cleaning up old containers..."
docker container prune -f 2>/dev/null || true
echo ""

# Step 7: Verify installation
echo "✅ Verification:"
echo "   docker compose version: $(docker compose version --short 2>/dev/null || echo 'not installed')"
echo "   docker-compose version: $(docker-compose --version 2>/dev/null || echo 'not installed')"
echo ""

echo "🎉 Done! Docker Compose V2 is now installed."
echo ""
echo "⚠️  IMPORTANT: Run 'source ~/.bashrc' or open a new terminal session"
echo ""
echo "🚀 You can now run: docker compose up -d"
