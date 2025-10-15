#!/bin/bash
# Setup script for uv-based development environment (Linux/macOS)
# Run this after installing uv: https://github.com/astral-sh/uv

set -e

echo "🚀 Setting up CGNS GUI development environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   Or visit: https://github.com/astral-sh/uv"
    exit 1
fi

echo "✓ uv found: $(uv --version)"

# Create virtual environment and install dependencies
echo ""
echo "📦 Installing project dependencies..."
uv sync --all-extras

echo "✓ Dependencies installed successfully"

# Check for pyCGNS
echo ""
echo "🔍 Checking for pyCGNS..."
if uv run python -c "import CGNS; print('✓ pyCGNS is available')" 2>/dev/null; then
    :
else
    echo "⚠️  pyCGNS not found (expected - not on PyPI)"
    echo ""
    echo "📝 To install pyCGNS, use one of these methods:"
    echo "   Method 1 (Recommended): conda install -c conda-forge pycgns"
    echo "   Method 2: Build from source at https://github.com/pyCGNS/pyCGNS"
    echo ""
    echo "   After installing pyCGNS, it will be available in this environment."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Quick start commands:"
echo "   uv run cgns-gui              # Run the application"
echo "   uv run pytest                # Run tests"
echo "   uv run ruff check .          # Lint code"
echo "   uv run python -m cgns_gui.app # Run with module path"
echo ""
echo "   Or activate the environment:"
echo "   source .venv/bin/activate    # Then use python/pytest directly"
