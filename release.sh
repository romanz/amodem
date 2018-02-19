#!/bin/bash
set -eux
rm -rv dist/*
python3 setup.py sdist
gpg2 -v --detach-sign -a dist/*.tar.gz
twine upload dist/*
