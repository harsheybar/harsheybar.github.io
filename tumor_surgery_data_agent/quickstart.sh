#!/bin/bash
# Quick Start Script for Tumor Surgery Data Agent

set -e  # Exit on error

echo "=========================================="
echo "Tumor Surgery Data Agent - Quick Start"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python 3.8 or higher required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"
echo ""

# Check for Census API key
echo "Checking for Census API key..."
if [ -z "$CENSUS_API_KEY" ]; then
    echo "⚠ No Census API key found"
    echo "  To get a free API key:"
    echo "  1. Visit: https://api.census.gov/data/key_signup.html"
    echo "  2. Set the key: export CENSUS_API_KEY='your_key'"
    echo ""
    echo "  Continuing with mock data..."
    CENSUS_ARG=""
else
    echo "✓ Census API key found"
    CENSUS_ARG="--census-key $CENSUS_API_KEY"
fi
echo ""

# Create output directory
echo "Creating output directory..."
mkdir -p output
echo "✓ Output directory ready"
echo ""

# Run analysis
echo "=========================================="
echo "Running Analysis Pipeline"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Query data sources (using mock data where needed)"
echo "  2. Map surgical volumes to MSAs"
echo "  3. Identify healthcare coldspots"
echo "  4. Generate visualizations"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

python3 main.py $CENSUS_ARG

echo ""
echo "=========================================="
echo "Analysis Complete!"
echo "=========================================="
echo ""
echo "Results saved to: output/"
echo ""
echo "Generated files:"
ls -lh output/ 2>/dev/null || echo "  (No files generated)"
echo ""
echo "To view results:"
echo "  - Open output/summary_table.html in a browser"
echo "  - View output/coldspot_heatmap.png"
echo "  - Check output/coldspot_report.csv for detailed data"
echo ""
echo "To run again with your own API keys:"
echo "  python3 main.py --census-key YOUR_KEY"
echo ""
echo "For more options:"
echo "  python3 main.py --help"
echo ""
