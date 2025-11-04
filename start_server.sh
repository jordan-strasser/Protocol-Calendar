#!/bin/bash
# Start the web UI server from the lab_calendar directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Starting Calendar Parser Web Server..."
echo "Open your browser and go to: http://localhost:8001"
echo ""
echo "To stop the server:"
echo "  - Press Ctrl+C in this terminal, OR"
echo "  - Run: ./stop_server.sh"
echo ""

python3 backend/calendar_server.py

