#!/bin/bash
set -u
set -e

run() {
	echo "SRC $HOST: $CMD" 1>&2
	ssh $HOST "$CMD"
}

run_src() {
	CMD="cd ~/Code/modem; $*"
	HOST="roman@localhost"
	run
}

run_dst() {
	CMD="cd ~/Code/modem; $*"
	HOST="roman@127.0.0.1"
	run
}

## generate 1Mbit of random data
run_src dd if=/dev/urandom of=data.send bs=125kB count=1 status=none
SRC_HASH=`run_src sha256sum data.send | ./colorhash.py`

# modulate data into audio file
run_src "./send.py <data.send >tx.int16"

# stop old recording and start a new one
run_src killall -q aplay || true
run_dst killall -q arecord || true

run_dst "./wave.py record rx.int16" &
sleep 1  # let rx.int16 be filled

# start the receiever
run_dst "./recv.py <rx.int16 >data.recv" &

# play the modulated data
run_src ./wave.py play   tx.int16

# stop recording after playing is over
run_src killall -q aplay || true
run_dst killall -q arecord || true

# verify transmittion
DST_HASH=`run_dst sha256sum data.recv | ./colorhash.py`

echo -e "$SRC_HASH\n$DST_HASH"