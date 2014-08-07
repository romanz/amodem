#!/bin/bash
killall -q aplay arecord
python -m amodem.calib send &
SENDER_PID=$!
python -m amodem.calib recv

kill -INT $SENDER_PID
