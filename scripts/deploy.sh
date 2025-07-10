#!/bin/bash

echo "🚀 Deploying MyBrain to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm i -g vercel
fi

# Build the project
echo "🔨 Building project..."
npm run build

# Deploy to Vercel
echo "☁️ Deploying to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
echo ""
echo "Don't forget to:"
echo "1. Set up environment variables in Vercel dashboard"
echo "2. Deploy the backend to Railway or similar"
echo "3. Update NEXT_PUBLIC_API_URL to point to your backend"