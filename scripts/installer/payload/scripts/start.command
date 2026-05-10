#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../cowagent"
"$SCRIPT_DIR/../python/bin/python3" app.py &
sleep 3
open http://localhost:9899/chat
