#!/bin/bash
set -u 
set -x
set -e 

dd if=/dev/urandom of=data.send bs=1024 count=8
python send.py
python recv.py
diff data.* || sha256sum data.*