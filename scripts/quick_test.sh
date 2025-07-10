#!/bin/bash
# Simple test script for MyBrain

echo "🧠 MyBrain Test Script"
echo "===================="

# Test 1: Backend Health
echo -e "\n1. Testing Backend Health..."
curl -s http://localhost:8000/health | python3 -m json.tool

# Test 2: Add a test document
echo -e "\n2. Adding test document..."
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MyBrain Test",
    "content": "This is a test document. MyBrain should remember this."
  }' -s | python3 -m json.tool

# Test 3: Search for the document
echo -e "\n3. Searching for test content..."
sleep 2  # Give time for indexing
curl -X POST http://localhost:8000/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "test document"}' -s | python3 -m json.tool

echo -e "\n✅ Tests complete!"
