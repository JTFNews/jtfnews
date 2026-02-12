#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Log file with timestamp
LOG_FILE="jtf.log"

# Clear old log and start fresh
> "$LOG_FILE"

echo "Starting JTF News... (logging to $LOG_FILE)"
echo "Started at $(date)" >> "$LOG_FILE"

# Run python, capture both stdout and stderr to log AND terminal
python3 main.py 2>&1 | tee -a "$LOG_FILE"
