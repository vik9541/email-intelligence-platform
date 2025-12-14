#!/bin/bash

# Pre-commit security checks

set -e

echo "🔒 Running pre-commit security checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check for secrets in staged files
echo "🔑 Checking for secrets..."
if git diff --cached --name-only -z | xargs -0 grep -iE "(password|api_key|secret|token|private_key|credential)" 2>/dev/null; then
    echo -e "${RED}❌ Potential secrets found in staged files!${NC}"
    echo "Please review and remove any sensitive data before committing."
    exit 1
fi
echo -e "${GREEN}✅ No secrets detected${NC}"

# 2. Check for large files
echo "📦 Checking for large files..."
MAX_SIZE=5242880  # 5MB
LARGE_FILES=$(git diff --cached --name-only | while read file; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt "$MAX_SIZE" ]; then
            echo "$file ($size bytes)"
        fi
    fi
done)

if [ -n "$LARGE_FILES" ]; then
    echo -e "${YELLOW}⚠️  Large files detected:${NC}"
    echo "$LARGE_FILES"
    echo "Consider using Git LFS for large files."
fi

# 3. Run Bandit (if installed)
if command -v bandit &> /dev/null; then
    echo "🚨 Running Bandit SAST..."
    if bandit -r app/ -q -f screen 2>/dev/null; then
        echo -e "${GREEN}✅ Bandit scan passed${NC}"
    else
        echo -e "${RED}❌ Bandit found security issues${NC}"
        echo "Run 'bandit -r app/' for details"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Bandit not installed, skipping SAST${NC}"
fi

# 4. Check Python imports for dangerous modules
echo "🐍 Checking Python imports..."
DANGEROUS_IMPORTS=$(git diff --cached --name-only | grep "\.py$" | while read file; do
    if [ -f "$file" ]; then
        grep -n "import pickle\|import marshal\|import shelve\|eval(\|exec(" "$file" 2>/dev/null
    fi
done)

if [ -n "$DANGEROUS_IMPORTS" ]; then
    echo -e "${YELLOW}⚠️  Potentially dangerous Python imports detected:${NC}"
    echo "$DANGEROUS_IMPORTS"
    echo "Review these carefully for security implications."
fi

# 5. Check for TODO/FIXME comments
echo "📝 Checking for TODO/FIXME..."
TODOS=$(git diff --cached --name-only | while read file; do
    if [ -f "$file" ]; then
        grep -Hn "TODO\|FIXME\|XXX\|HACK" "$file" 2>/dev/null
    fi
done)

if [ -n "$TODOS" ]; then
    echo -e "${YELLOW}⚠️  Found TODO/FIXME comments:${NC}"
    echo "$TODOS"
fi

# 6. Validate JSON/YAML files
echo "📄 Validating configuration files..."
git diff --cached --name-only | grep "\.json$" | while read file; do
    if [ -f "$file" ]; then
        if ! python -m json.tool "$file" > /dev/null 2>&1; then
            echo -e "${RED}❌ Invalid JSON: $file${NC}"
            exit 1
        fi
    fi
done

git diff --cached --name-only | grep "\.ya\?ml$" | while read file; do
    if [ -f "$file" ]; then
        if command -v yamllint &> /dev/null; then
            if ! yamllint "$file" > /dev/null 2>&1; then
                echo -e "${YELLOW}⚠️  YAML issues in: $file${NC}"
            fi
        fi
    fi
done

echo -e "${GREEN}✅ All pre-commit security checks passed!${NC}"
exit 0
