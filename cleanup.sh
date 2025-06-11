#!/bin/bash

# Files/directories to keep
keep_files=(
    "favorites"
    "config"
    "logs"
    "output"
    "Dockerfile"
    "docker-compose.yml"
    "requirements-custom.txt"
    ".gitignore"
    "cleanup.sh"
    ".env"
    "ca-state-parks.yaml"
    "camply_config.yaml"
    "top-rec-areas.yaml"
    "weekend-alerts.yaml"
    "rec-favorites.json"
)

# Create temporary directory for backup
mkdir -p temp_backup
echo "Creating backup of important files..."

# Copy files to keep to backup
for file in "${keep_files[@]}"; do
    if [ -e "$file" ]; then
        cp -R "$file" temp_backup/
    fi
done

# Remove all files except the backup directory
echo "Cleaning up original repository files..."
find . -maxdepth 1 ! -name "." ! -name ".." ! -name "temp_backup" -exec rm -rf {} +

# Move files back from backup
echo "Restoring your custom files..."
mv temp_backup/* .
rm -rf temp_backup

# Initialize new git repository
echo "Initializing new git repository..."
git init
git add .
git commit -m "Initial commit with custom camply configuration"

echo "Cleanup complete! Your custom configuration is preserved and ready to use with the Docker container." 