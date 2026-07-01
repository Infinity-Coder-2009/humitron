# Windows build script for Humitron
Write-Host "Starting Windows build for Humitron..."

# Step 1: Install frontend dependencies
Write-Host "Installing frontend dependencies..."
npm install

# Step 2: Build the frontend
Write-Host "Building frontend..."
npm run build

# Step 3: Build the Tauri app
Write-Host "Building Tauri app for Windows..."
npm run tauri:build

Write-Host "Build complete! Check src-tauri/target/release/bundle/ for the installer."