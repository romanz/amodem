#!/bin/bash
set -x -u
SRC=`tempfile`
DST=`tempfile`
AUDIO=`tempfile`
dd if=/dev/urandom of=$SRC bs=1kB count=1000
export BITRATE=80
time python -m cProfile -o send.prof amodem-cli send -l- -vv -i $SRC -o $AUDIO 2> send.log
echo -e "sort cumtime\nstats" | python -m pstats send.prof > send.prof.txt

time python -m cProfile -o recv.prof amodem-cli recv -l- -vv -i $AUDIO -o $DST 2> recv.log
echo -e "sort cumtime\nstats" | python -m pstats recv.prof > recv.prof.txt

diff $SRC $DST || echo "ERROR!"
rm $SRC $DST $AUDIO
