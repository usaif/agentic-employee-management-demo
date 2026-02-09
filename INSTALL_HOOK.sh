#!/bin/bash
# Installation script for write capability pre-commit hook

set -e

echo "=================================================="
echo "Installing Pre-Commit Hook for Write Capabilities"
echo "=================================================="
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    if command -v uv &> /dev/null; then
        uv pip install pre-commit
    elif command -v pip &> /dev/null; then
        pip install pre-commit
    else
        echo "Error: Neither uv nor pip found. Please install one of them first."
        exit 1
    fi
else
    echo "✓ pre-commit is already installed"
fi

echo ""

# Install the hook
echo "Installing git hooks..."
pre-commit install

echo ""
echo "=================================================="
echo "Installation Complete!"
echo "=================================================="
echo ""
echo "Testing the hook..."
pre-commit run check-write-capabilities --all-files

echo ""
echo "=================================================="
echo "Next Steps"
echo "=================================================="
echo ""
echo "1. The hook will now run automatically on every commit"
echo "2. Try the demos:"
echo "   - bash hooks/scripts/demo.sh"
echo "   - bash hooks/scripts/demo_auth_hook.sh"
echo "3. Read the docs:"
echo "   - hooks/docs/quickstart.md (quick start guide)"
echo "   - hooks/docs/all-hooks-summary.md (overview)"
echo "   - hooks/README.md (main documentation)"
echo ""
echo "4. Test your understanding:"
echo "   - Add a new write operation to app/api/employee.py"
echo "   - Try to commit without tests (should be blocked)"
echo "   - Add tests to tests/ directory"
echo "   - Commit again (should succeed)"
echo ""
echo "Happy coding! 🚀"
