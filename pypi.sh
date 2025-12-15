#!/bin/bash
# pypi.sh - Build and upload netconduit to PyPI
# Usage: ./pypi.sh

set -e
source .venv/bin/activate
echo "=========================================="
echo "  netconduit PyPI Upload Script"
echo "=========================================="

# Check if twine is installed
if ! command -v twine &> /dev/null; then
    echo "Installing twine..."
    pip install twine
fi

# Check if build is installed
if ! command -v python -m build &> /dev/null; then
    echo "Installing build..."
    pip install build
fi

# Clean previous builds
echo ""
echo "[1/4] Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Build the package
echo ""
echo "[2/4] Building package..."
python -m build

# Show what was built
echo ""
echo "[3/4] Built packages:"
ls -la dist/

# Upload to PyPI
echo ""
echo "[4/4] Uploading to PyPI..."

twine upload dist/*

echo ""
echo "=========================================="
echo "  Upload complete!"
echo "=========================================="
echo ""
echo "Install with: pip install netconduit"
echo ""
