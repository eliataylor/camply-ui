# my_camping_favs/scripts/setup_env.sh
#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define virtual environment and camply paths
VENV_DIR=".venv"
CAMPLY_REPO_DIR="camply"

echo "Setting up Python environment for my_camping_favs..."

# 1. Create and activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Ensure pip and setuptools are up to date in the venv
echo "Updating pip and setuptools..."
pip install --upgrade pip setuptools

# 2. Clone camply if it doesn't exist
if [ ! -d "$CAMPLY_REPO_DIR" ]; then
    echo "Cloning camply repository..."
    git clone https://github.com/juftin/camply.git "$CAMPLY_REPO_DIR"
else
    echo "camply repository already exists."
    # Optional: Pull latest camply updates
    # echo "Pulling latest camply changes..."
    # (cd "$CAMPLY_REPO_DIR" && git pull)
fi

# 3. Install my_camping_favs in editable mode
echo "Installing my_camping_favs in editable mode..."
pip install -e .

# 4. Install camply in editable mode
echo "Installing camply in editable mode..."
pip install -e "./$CAMPLY_REPO_DIR"

echo "Setup complete. To activate: 'source ./.venv/bin/activate'"
echo "To run your script: 'python src/californias_best.py'"