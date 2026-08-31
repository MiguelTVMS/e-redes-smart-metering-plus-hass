#!/bin/bash
# Script to install the pre-commit hook

set -e

HOOK_SOURCE="scripts/pre-commit"
HOOK_DEST=".git/hooks/pre-commit"

echo "🔧 Installing pre-commit hook..."

# Check if .git directory exists
if [ ! -d ".git" ]; then
    echo "❌ Error: .git directory not found. Are you in the repository root?"
    exit 1
fi

# Check if hook source exists
if [ ! -f "$HOOK_SOURCE" ]; then
    echo "❌ Error: Hook source file not found at $HOOK_SOURCE"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy the hook
cp "$HOOK_SOURCE" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "The hook will now run automatically before each commit."
echo "It will check:"
echo "  - Black formatting"
echo "  - isort import ordering"
echo "  - Ruff linting"
echo "  - Pytest tests (when test or source files are staged)"
echo ""
echo "To bypass the hook (not recommended), use: git commit --no-verify"
