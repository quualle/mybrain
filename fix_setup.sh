#!/bin/bash

echo "🔧 Fixing MyBrain Setup"
echo "======================"

# Make sure we're in virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies without psycopg2
echo "📦 Installing Python dependencies (without psycopg2)..."
pip install -r requirements.txt

# Try to install psycopg2-binary separately
echo "📦 Trying alternative PostgreSQL adapter..."
pip install psycopg2-binary || pip install psycopg-binary || echo "⚠️  psycopg2 installation failed - using asyncpg only"

echo ""
echo "✅ Fix complete!"
echo ""
echo "Now run: ./scripts/check_setup.py"