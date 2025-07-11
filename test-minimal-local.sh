#!/bin/bash

# Test-Script für die minimale Version lokal

echo "🧪 Testing MyBrain Minimal Version locally..."

# Backend starten
echo "📦 Installing minimal dependencies..."
cd backend
pip install -r ../requirements-performance.txt

echo "🚀 Starting backend..."
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Warte bis Backend bereit ist
echo "⏳ Waiting for backend to start..."
sleep 5

# Test Backend Health
echo "🏥 Testing backend health..."
curl http://localhost:8000/health

echo ""
echo "✅ Backend läuft auf http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "🎯 Frontend kannst du separat starten mit: npm run dev"
echo ""
echo "🛑 Zum Beenden: CTRL+C"

# Warte auf Beenden
wait $BACKEND_PID