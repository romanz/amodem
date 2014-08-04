#!/bin/bash
set -u
set -e

run() {
	echo "SRC $HOST ($DIR): $*" 1>&2
	if [ "$HOST" == "localhost" ]; then
		echo "$*" | bash
	else
		ssh $HOST "cd $DIR; $*"
	fi
}

run_src() {
	DIR=${SRC_DIR:-"$PWD"}
	HOST=${SRC_HOST:-localhost}
	run "$*"
}

run_dst() {
	DIR=${DST_DIR:-"$PWD"}
	HOST=${DST_HOST:-localhost}
	run "$*"
}

TEST_DIR=test_results
run_src mkdir -p $TEST_DIR
run_dst mkdir -p $TEST_DIR

## generate 1Mbit of random data
run_src dd if=/dev/urandom of=$TEST_DIR/data.send bs=125kB count=1 status=none
SRC_HASH=`run_src sha256sum $TEST_DIR/data.send`

# modulate data into audio file
run_src "./send.py <$TEST_DIR/data.send >$TEST_DIR/audio.send"

# stop old recording and start a new one
run_src killall -q aplay || true
run_dst killall -q arecord || true

run_dst "./wave.py record $TEST_DIR/audio.recv" &
sleep 1  # let audio.recv be filled

# play the modulated data
run_src ./wave.py play   $TEST_DIR/audio.send &

# start the receiever
run_dst "./recv.py <$TEST_DIR/audio.recv >$TEST_DIR/data.recv"

# stop recording after playing is over
run_src killall -q aplay || true
run_dst killall -q arecord || true

# verify transmittion
DST_HASH=`run_dst sha256sum $TEST_DIR/data.recv`

echo -e "$SRC_HASH\n$DST_HASH"
