#!/bin/bash
# Install Git hooks for FDA Tools plugin

set -e

# Find Git directory
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo ".git")

if [ ! -d "$GIT_DIR" ]; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Create pre-commit hook
cat > "$GIT_DIR/hooks/pre-commit" << 'HOOK_EOF'
#!/bin/bash
# Git pre-commit hook: Check version consistency

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running pre-commit checks...${NC}"

# Get the root of the repository
REPO_ROOT=$(git rev-parse --show-toplevel)

# Change to repository root
cd "$REPO_ROOT"

# Find project root (where scripts/ directory is)
if [ -d "plugins/fda-tools/scripts" ]; then
    PROJECT_ROOT="plugins/fda-tools"
elif [ -d "scripts" ]; then
    PROJECT_ROOT="."
else
    echo -e "${YELLOW}Warning: Could not find scripts directory, skipping version check${NC}"
    exit 0
fi

# Check if version files are being committed
VERSION_FILES_CHANGED=$(git diff --cached --name-only | grep -E "(scripts/version\.py|\.claude-plugin/plugin\.json|CHANGELOG\.md)" || true)

if [ -n "$VERSION_FILES_CHANGED" ]; then
    echo -e "${YELLOW}Version-related files changed, checking consistency...${NC}"
    
    # Run version consistency check
    if ! python3 "$PROJECT_ROOT/scripts/check_version.py"; then
        echo -e "${RED}✗ Version consistency check failed!${NC}"
        echo -e "${YELLOW}Fix version mismatches before committing.${NC}"
        echo -e "Run: ${GREEN}python3 scripts/update_version.py X.Y.Z${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Version consistency check passed${NC}"
fi

exit 0
HOOK_EOF

# Make hook executable
chmod +x "$GIT_DIR/hooks/pre-commit"

echo "✓ Git pre-commit hook installed successfully"
echo "  Location: $GIT_DIR/hooks/pre-commit"
echo ""
echo "The hook will run automatically before each commit."
echo "To bypass the hook (not recommended), use: git commit --no-verify"
