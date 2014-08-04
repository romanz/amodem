#!/bin/bash
python -m cProfile -o result.prof $*

echo "sort time
stats 20" | python -m pstats result.prof 1>&2
