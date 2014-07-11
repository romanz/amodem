#!/bin/bash
set -u 
set -e 

dd if=/dev/urandom of=data.send bs=1024 count=16
./send.py tx.int16

killall arecord aplay || true

./wave.py record rx.int16 &
./wave.py play   tx.int16
sleep 1

killall arecord aplay || true

./recv.py rx.int16
./errors.py data.* 
if [ -z $? ]; then
	./show.py tx.int16 rx.int16
fi
