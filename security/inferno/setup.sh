#!/bin/bash
# Setup script for Inferno ONC g(10) Test Kit
# Run this ONCE before using docker compose --profile scan up inferno
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$SCRIPT_DIR/onc-certification-g10-test-kit"

if [ -d "$REPO_DIR" ]; then
  echo "Inferno g(10) test kit already cloned at $REPO_DIR"
  echo "Pulling latest..."
  cd "$REPO_DIR" && git pull
else
  echo "Cloning ONC Certification g(10) Test Kit..."
  git clone https://github.com/onc-healthit/onc-certification-g10-test-kit.git "$REPO_DIR"
fi

echo ""
echo "Setup complete. Run Inferno with:"
echo "  docker compose --profile scan up inferno"
echo ""
echo "NOTE: Inferno requires ~4GB RAM. Stop other heavy services first if on 8GB system."
