#!/bin/bash
set -u
set -e

# generate 1Mbit of random data
dd if=/dev/urandom of=data.send bs=125kB count=1 status=none

# modulate data into audio file
./send.py <data.send >tx.int16

# stop old recording and start a new one
killall -q arecord aplay || true
./wave.py record rx.int16 &
sleep 1  # let rx.int16 be filled

# start the receiever
./recv.py <rx.int16 >data.recv &

# play the modulated data
./wave.py play   tx.int16

# stop recording after playing is over
killall -q arecord aplay || true

# verify transmittion
./errors.py data.*
sha256sum data.* | ./colorhash.py
if [ -z $? ]; then
	./show.py tx.int16 rx.int16
fi

