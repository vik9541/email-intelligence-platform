#!/bin/bash
#
# CONNECT TO DIGITALOCEAN SERVER
# Helper script for SSH connection
#

set -e

echo "🔐 DigitalOcean Server Connection Helper"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if credentials are available
if [ -z "$DO_SSH_HOST" ]; then
    echo -e "${RED}❌ Error: DO_SSH_HOST not set${NC}"
    echo ""
    echo "Please set environment variables:"
    echo "  export DO_SSH_HOST='your-server-ip'"
    echo "  export DO_SSH_USER='root'  # or ubuntu"
    echo "  export DO_SSH_PORT='22'"
    echo ""
    echo "Or get them from GitHub Secrets:"
    echo "  GitHub → Settings → Secrets → DO_SSH_HOST"
    exit 1
fi

# Set defaults
SSH_USER="${DO_SSH_USER:-root}"
SSH_PORT="${DO_SSH_PORT:-22}"
SSH_KEY="${DO_SSH_KEY_PATH:-$HOME/.ssh/digitalocean_key}"

echo "Connection details:"
echo "  Host: $DO_SSH_HOST"
echo "  User: $SSH_USER"
echo "  Port: $SSH_PORT"
echo "  Key:  $SSH_KEY"
echo ""

# Check if key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}⚠️  SSH key not found at: $SSH_KEY${NC}"
    echo ""
    echo "To create the key:"
    echo "  1. Get DO_SSH_PRIVATE_KEY from GitHub Secrets"
    echo "  2. Save it:"
    echo "     cat > $SSH_KEY << 'EOF'"
    echo "     [paste key content]"
    echo "     EOF"
    echo "  3. Set permissions:"
    echo "     chmod 600 $SSH_KEY"
    echo ""
    exit 1
fi

# Check key permissions
KEY_PERMS=$(stat -c '%a' "$SSH_KEY" 2>/dev/null || stat -f '%A' "$SSH_KEY" 2>/dev/null)
if [ "$KEY_PERMS" != "600" ]; then
    echo -e "${YELLOW}⚠️  Fixing key permissions (currently $KEY_PERMS)${NC}"
    chmod 600 "$SSH_KEY"
    echo -e "${GREEN}✅ Key permissions fixed${NC}"
fi

echo ""
echo "Connecting..."
echo ""

# Connect
ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "$@"
