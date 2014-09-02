#!/bin/bash
killall -q aplay arecord

./scripts/calib.py send &
SENDER_PID=$!
echo "Playing audio (PID=${SENDER_PID})..."

echo "Recording audio (Stop with Ctrl+C)..."
./scripts/calib.py recv

echo "Stopping player..."
kill -INT $SENDER_PID
