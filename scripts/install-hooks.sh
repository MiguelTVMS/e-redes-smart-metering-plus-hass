#!/bin/bash
# Script to install the pre-commit hook

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

HOOK_SOURCE="scripts/pre-commit"

echo "🔧 Installing pre-commit hook..."

# Confirm that this is a Git checkout, including linked worktrees.
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "❌ Error: Git repository not found."
    exit 1
fi

HOOK_DEST="$(git rev-parse --git-path hooks/pre-commit)"
case "$HOOK_DEST" in
    /*) ;;
    *) HOOK_DEST="$PROJECT_DIR/$HOOK_DEST" ;;
esac

# Check if hook source exists
if [ ! -f "$HOOK_SOURCE" ]; then
    echo "❌ Error: Hook source file not found at $HOOK_SOURCE"
    exit 1
fi

# Create the resolved hooks directory if it doesn't exist.
mkdir -p "$(dirname "$HOOK_DEST")"

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
