#!/bin/bash
set -x
CREATED=1460731897  # needed for consistent public key creation
NAME="trezor_key"  # will be used as GPG user id and public key name

echo "Hello GPG World!" > EXAMPLE
# Create, sign and export the public key
./signer.py $NAME --time $CREATED --public-key --verbose

# Install GPG v2.1 (modern) and import the public key
gpg2 --import $NAME.pub
gpg2 --list-keys $NAME

# Perform actual GPG signature using TREZOR
./signer.py $NAME --file EXAMPLE --verbose
./check.py $NAME.pub EXAMPLE.sig  # pure Python verification

# gpg2 --edit-key trezor_key trust  # optional: mark it as trusted
gpg2 --verify EXAMPLE.sig
