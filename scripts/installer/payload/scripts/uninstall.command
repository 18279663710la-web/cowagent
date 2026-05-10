#!/bin/bash
echo "Uninstalling CowAgent..."
rm -f ~/Desktop/CowAgent.command
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$SCRIPT_DIR/.."
echo "CowAgent has been uninstalled."
