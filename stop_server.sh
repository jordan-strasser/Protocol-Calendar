#!/bin/bash
# Stop the calendar server

PORT=8001

echo "Stopping Calendar Parser Web Server on port $PORT..."

# Find and kill processes using the port
PIDS=$(lsof -ti:$PORT 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "No server found running on port $PORT"
    exit 0
fi

for PID in $PIDS; do
    # Check if it's actually our calendar server
    if ps -p $PID -o command= | grep -q "calendar_server"; then
        echo "Stopping server (PID: $PID)..."
        kill $PID 2>/dev/null
        sleep 1
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
        fi
        echo "✓ Server stopped"
    else
        echo "Warning: Process $PID on port $PORT is not calendar_server"
        echo "  Not stopping it. Use 'lsof -ti:$PORT | xargs kill' to force stop."
    fi
done

