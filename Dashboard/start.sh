#!/bin/bash

# JASON Dashboard Startup Script

echo "=========================================="
echo "  JASON Dashboard - Startup Script"
echo "  Just A Simple Ordinary Network"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if [ ! -f "venv/lib/python*/site-packages/flask/__init__.py" ]; then
    echo ""
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo ""
        echo "⚠️  .env file not found. Using defaults from .env.example"
        echo "   You can copy .env.example to .env and customize settings"
    fi
fi

echo ""
echo "=========================================="
echo "  Starting JASON Dashboard Backend..."
echo "=========================================="
echo ""
echo "📍 Dashboard URL: http://localhost:5000"
echo "📡 API Endpoints: http://localhost:5000/api/*"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Flask application
python main.py

