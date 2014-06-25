#!/bin/bash
(while [ true ]; do cat $1; done ) | aplay -q -f S16_LE -c 1 -r 32000
