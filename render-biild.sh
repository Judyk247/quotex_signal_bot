#!/bin/bash
echo "=== Starting Build Process ==="

# Set Python path explicitly
export PYTHONPATH=/opt/render/project/src

# Upgrade pip and setuptools first
python -m pip install --upgrade pip setuptools wheel --no-cache-dir

# Install numpy first (required for pandas)
pip install numpy==2.0.0 --no-cache-dir

# Install other requirements
pip install -r requirements.txt --no-cache-dir

echo "=== Build Completed Successfully ==="
