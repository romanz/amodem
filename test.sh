#!/bin/bash
set -u 
set -e 

dd if=/dev/urandom of=data.send bs=1024 count=1024 status=none
./send.py tx.int16 < data.send

killall -q arecord aplay || true

./wave.py record rx.int16 &
./wave.py play   tx.int16
sleep 1

killall -q arecord aplay || true

./recv.py rx.int16 > data.recv
./errors.py data.* 
if [ -z $? ]; then
	./show.py tx.int16 rx.int16
fi
