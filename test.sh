#!/bin/bash
set -u 
set -e 

dd if=/dev/urandom of=data.send bs=1024 count=1
./send.py

./wave.py record rx.int16 &
PID=$!

./wave.py play   tx.int16
sleep 1
kill -INT $PID

./recv.py
./errors.py data.* 
if [ -z $? ]; then
	./show.py tx.int16 rx.int16
fi