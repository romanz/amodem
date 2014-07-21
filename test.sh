#!/bin/bash
set -u 
set -e 

dd if=/dev/urandom of=data.send bs=125kB count=1 status=none
./send.py tx.int16 < data.send

killall -q arecord aplay || true

./wave.py record rx.int16 &
sleep 1

./recv.py rx.int16 > data.recv &
./wave.py play   tx.int16 

killall -q arecord aplay || true

./errors.py data.* 
sha256sum data.* | ./colorhash.py
if [ -z $? ]; then
	./show.py tx.int16 rx.int16
fi

