#!/bin/bash
killall -q aplay arecord
python -m calib send &
SENDER_PID=$!
python -m calib recv

kill -INT $SENDER_PID
