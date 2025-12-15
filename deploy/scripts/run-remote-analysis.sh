#!/bin/bash
#
# RUN REMOTE SERVER ANALYSIS
# Execute analysis scripts on remote DigitalOcean server
#

set -e

echo "🔍 Remote Server Analysis"
echo "=========================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check environment
if [ -z "$DO_SSH_HOST" ]; then
    echo -e "${RED}❌ Error: Environment variables not set${NC}"
    echo ""
    echo "Required:"
    echo "  export DO_SSH_HOST='your-server-ip'"
    echo "  export DO_SSH_USER='root'"
    echo ""
    exit 1
fi

SSH_USER="${DO_SSH_USER:-root}"
SSH_PORT="${DO_SSH_PORT:-22}"
SSH_KEY="${DO_SSH_KEY_PATH:-$HOME/.ssh/digitalocean_key}"

echo -e "${BLUE}Server: $DO_SSH_HOST${NC}"
echo -e "${BLUE}User:   $SSH_USER${NC}"
echo ""

# Analysis type
ANALYSIS_TYPE="${1:-quick}"

case "$ANALYSIS_TYPE" in
    quick)
        echo "Running: Quick Check (~30 seconds)"
        SCRIPT="quick-check.sh"
        ;;
    full)
        echo "Running: Full Analysis (~2-3 minutes)"
        SCRIPT="00-analyze-server.sh"
        ;;
    *)
        echo "Usage: $0 [quick|full]"
        echo ""
        echo "  quick  - Fast check (30 seconds)"
        echo "  full   - Complete analysis (2-3 minutes)"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}Connecting to server...${NC}"
echo ""

# Create temporary script to run remotely
cat > /tmp/remote-analysis.sh << 'REMOTE_SCRIPT'
#!/bin/bash

# Find project directory
PROJECT_DIR=""
for dir in /opt/email-service ~/email-service /var/www/email-service; do
    if [ -d "$dir" ]; then
        PROJECT_DIR="$dir"
        break
    fi
done

if [ -z "$PROJECT_DIR" ]; then
    echo "❌ Error: email-service directory not found"
    echo ""
    echo "Tried locations:"
    echo "  /opt/email-service"
    echo "  ~/email-service"
    echo "  /var/www/email-service"
    echo ""
    echo "Please clone the repository:"
    echo "  cd /opt"
    echo "  git clone https://github.com/[username]/email-service.git"
    exit 1
fi

echo "✅ Found project: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

# Ensure scripts are executable
chmod +x deploy/scripts/*.sh 2>/dev/null || true

# Run analysis script
SCRIPT_PATH="deploy/scripts/$1"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: Script not found: $SCRIPT_PATH"
    echo ""
    echo "Available scripts:"
    ls -1 deploy/scripts/*.sh 2>/dev/null || echo "  None found"
    exit 1
fi

echo "Running: $SCRIPT_PATH"
echo ""

"./$SCRIPT_PATH"

# If full analysis, show where report is saved
if [ "$1" = "00-analyze-server.sh" ]; then
    echo ""
    echo "=========================================="
    echo "📄 Report saved to:"
    ls -1t /tmp/server-analysis-*.txt 2>/dev/null | head -1 || echo "  (Report file not found)"
fi
REMOTE_SCRIPT

# Upload and execute
echo -e "${YELLOW}Uploading script...${NC}"
scp -i "$SSH_KEY" -P "$SSH_PORT" /tmp/remote-analysis.sh "$SSH_USER@$DO_SSH_HOST:/tmp/" >/dev/null 2>&1

echo -e "${YELLOW}Executing...${NC}"
echo ""
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "bash /tmp/remote-analysis.sh $SCRIPT"

# Download full report if available
if [ "$ANALYSIS_TYPE" = "full" ]; then
    echo ""
    echo -e "${YELLOW}Downloading report...${NC}"
    
    REPORT_FILE=$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "ls -1t /tmp/server-analysis-*.txt 2>/dev/null | head -1")
    
    if [ -n "$REPORT_FILE" ]; then
        LOCAL_REPORT="server-analysis-$(date +%Y%m%d-%H%M%S).txt"
        scp -i "$SSH_KEY" -P "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST:$REPORT_FILE" "./$LOCAL_REPORT" >/dev/null 2>&1
        echo -e "${GREEN}✅ Report downloaded: $LOCAL_REPORT${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Analysis complete!${NC}"
