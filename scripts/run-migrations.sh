#!/bin/bash

# Database migration script

set -e

echo "🔄 Running database migrations..."

# Set defaults
DB_HOST=${DB_HOST:-postgres}
DB_USER=${DB_USER:-postgres}
DB_NAME=${DB_NAME:-email_db}

# 1. Check current schema version
echo "📋 Current schema version:"
alembic current || echo "No migrations applied yet"

# 2. List pending migrations
echo "📝 Pending migrations:"
alembic history

# 3. Create backup before migration
echo "💾 Creating backup before migration..."
BACKUP_FILE="backup-pre-migration-$(date +%Y%m%d-%H%M%S).sql"

if [ -n "$DB_PASSWORD" ]; then
    export PGPASSWORD=$DB_PASSWORD
    pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > $BACKUP_FILE
    gzip $BACKUP_FILE
    echo "✅ Backup created: ${BACKUP_FILE}.gz"
else
    echo "⚠️  DB_PASSWORD not set, skipping backup"
fi

# 4. Dry-run (show SQL)
echo "🔍 Migration SQL (dry-run):"
alembic upgrade head --sql

# 5. Execute migrations
echo "⬆️  Upgrading schema..."
alembic upgrade head

# 6. Verify
echo "✅ Migration completed!"
alembic current

# 7. Test database connection
echo "🧪 Testing database connection..."
python -c "
from sqlalchemy import create_engine
import os
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/email_db')
engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('✅ Database connection successful')
" || echo "❌ Database connection failed"

echo "✅ All migrations successful!"
