#!/bin/bash
echo "🔨 Azure Custom Build Script - Building Next.js Frontend"

# Change to frontend directory
cd src/webui/app

# Check if Node.js is available
if command -v node &> /dev/null; then
    echo "✅ Node.js version: $(node --version)"
else
    echo "❌ Node.js not found in Azure build environment"
    exit 1
fi

# Check if npm is available
if command -v npm &> /dev/null; then
    echo "✅ npm version: $(npm --version)"
else
    echo "❌ npm not found in Azure build environment"
    exit 1
fi

# Install dependencies
echo "📦 Installing Node.js dependencies..."
npm ci

# Build the frontend
echo "🏗️ Building Next.js frontend..."
npm run build

# Verify build output
if [ -d "out" ]; then
    echo "✅ Frontend build successful!"
    echo "📁 Build output:"
    ls -la out/
    echo "📄 Key files:"
    ls -la out/index.html out/favicon.ico 2>/dev/null || echo "Some files may be missing"
else
    echo "❌ Frontend build failed - no 'out' directory found"
    exit 1
fi

echo "🎉 Azure custom build script completed successfully!"