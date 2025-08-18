#!/bin/bash
set -e  # Exit on any error

echo "🔨 Azure Custom Build Script - Building Next.js Frontend"

# Check Node.js version requirement
echo "🔍 Checking Node.js version requirements..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js version: $NODE_VERSION"
    
    # Extract major version number (e.g., v14.19.2 -> 14)
    NODE_MAJOR=$(echo $NODE_VERSION | sed 's/v\([0-9]*\).*/\1/')
    
    if [ "$NODE_MAJOR" -lt 18 ]; then
        echo "❌ Node.js $NODE_VERSION is too old. Required: >= 18.0.0"
        echo "🔧 Azure is using an outdated Node.js version."
        echo "💡 This may require updating Azure App Service Node.js runtime."
        exit 1
    fi
else
    echo "❌ Node.js not found in Azure build environment"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    echo "✅ npm version: $(npm --version)"
else
    echo "❌ npm not found in Azure build environment"
    exit 1
fi

# Change to frontend directory
echo "📂 Changing to frontend directory..."
cd src/webui/app

# Clean npm cache to avoid corrupted package issues
echo "🧹 Cleaning npm cache..."
npm cache clean --force || echo "⚠️ Cache clean failed, continuing..."

# Remove node_modules and package-lock.json to ensure clean install
echo "🗑️ Removing old dependencies..."
rm -rf node_modules package-lock.json

# Install dependencies with verbose logging
echo "📦 Installing Node.js dependencies..."
npm install --verbose

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
    
    # Count files for verification
    FILE_COUNT=$(find out -type f | wc -l)
    echo "📊 Total files in build: $FILE_COUNT"
else
    echo "❌ Frontend build failed - no 'out' directory found"
    echo "📁 Current directory contents:"
    ls -la
    exit 1
fi

echo "🎉 Azure custom build script completed successfully!"