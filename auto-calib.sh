#!/bin/bash
killall -q aplay arecord
./calib.py send &
SENDER_PID=$!
./calib.py recv

kill -INT $SENDER_PID
