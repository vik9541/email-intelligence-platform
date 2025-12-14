#!/bin/bash

# Database recovery procedure
# Usage: bash restore-database.sh backup-20251214-020000.sql.gz

BACKUP_FILE=$1
DB_NAME="email_db"
DB_USER="postgres"
DB_HOST="postgres"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  exit 1
fi

echo "🔄 Starting database recovery..."

# 1. Download backup from S3
echo "📥 Downloading backup from S3..."
aws s3 cp s3://email-backups/$BACKUP_FILE ./

# 2. Decompress
echo "🗜️  Decompressing..."
gunzip $BACKUP_FILE
RESTORE_FILE="${BACKUP_FILE%.gz}"

# 3. Stop application
echo "⏸️  Stopping application..."
kubectl scale deployment email-intelligence --replicas=0

# 4. Drop existing database
echo "🗑️  Dropping existing database..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"

# 5. Create new database
echo "📊 Creating new database..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE $DB_NAME;"

# 6. Restore from backup
echo "♻️  Restoring from backup..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER $DB_NAME < $RESTORE_FILE

# 7. Verify
echo "✅ Verifying backup..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER $DB_NAME -c "SELECT COUNT(*) FROM observations;" 

# 8. Start application
echo "🚀 Starting application..."
kubectl scale deployment email-intelligence --replicas=1

# 9. Health check
echo "💚 Waiting for application to be healthy..."
sleep 30
curl http://localhost:8000/health

echo "✅ Recovery completed successfully!"
