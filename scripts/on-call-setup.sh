#!/bin/bash

# Setup on-call environment

echo "🚀 Setting up on-call access..."

# 1. kubectl access
echo "Configuring kubectl..."
kubectl cluster-info

# 2. SSH keys
echo "Adding SSH keys..."
ssh-add ~/.ssh/id_rsa

# 3. Slack integration
echo "Slack webhook: $SLACK_WEBHOOK_URL"

# 4. Emergency contacts
cat > ~/.on-call-phone.txt << 'EOF'
Incident Commander: +1-XXX-XXX-XXXX
Engineering Lead: +1-XXX-XXX-XXXX
Database Admin: +1-XXX-XXX-XXXX
EOF

# 5. Test access
echo "Testing access..."
kubectl get pods
curl http://localhost:3000/api/health  # Grafana

echo "✅ On-call setup complete!"
echo "You can start your shift now 🎯"
