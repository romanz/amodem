#!/bin/bash
killall -q aplay arecord
./calib.py send &
./calib.py recv
killall -q aplay arecord