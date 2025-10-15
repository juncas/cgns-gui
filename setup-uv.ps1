# Setup script for uv-based development environment
# Run this after installing uv: https://github.com/astral-sh/uv

# This script sets up the development environment using uv
Write-Host "🚀 Setting up CGNS GUI development environment with uv..." -ForegroundColor Cyan

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "   PowerShell: irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Yellow
    Write-Host "   Or visit: https://github.com/astral-sh/uv" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ uv found: $(uv --version)" -ForegroundColor Green

# Create virtual environment and install dependencies
Write-Host "`n📦 Installing project dependencies..." -ForegroundColor Cyan
uv sync --all-extras

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Check for pyCGNS
Write-Host "`n🔍 Checking for pyCGNS..." -ForegroundColor Cyan
$pycgnsCheck = uv run python -c "import CGNS; print('✓ pyCGNS is available')" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host $pycgnsCheck -ForegroundColor Green
} else {
    Write-Host "⚠️  pyCGNS not found (expected - not on PyPI)" -ForegroundColor Yellow
    Write-Host "`n📝 To install pyCGNS, use one of these methods:" -ForegroundColor Yellow
    Write-Host "   Method 1 (Recommended): conda install -c conda-forge pycgns" -ForegroundColor White
    Write-Host "   Method 2: Build from source at https://github.com/pyCGNS/pyCGNS" -ForegroundColor White
    Write-Host "`n   After installing pyCGNS, it will be available in this environment." -ForegroundColor White
}

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "`n📚 Quick start commands:" -ForegroundColor Cyan
Write-Host "   uv run cgns-gui              # Run the application" -ForegroundColor White
Write-Host "   uv run pytest                # Run tests" -ForegroundColor White
Write-Host "   uv run ruff check .          # Lint code" -ForegroundColor White
Write-Host "   uv run python -m cgns_gui.app # Run with module path" -ForegroundColor White
Write-Host "`n   Or activate the environment:" -ForegroundColor White
Write-Host "   .venv\Scripts\Activate.ps1   # Then use python/pytest directly" -ForegroundColor White
