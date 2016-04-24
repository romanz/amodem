#!/bin/bash
set -x
CREATED=1460731897  # needed for consistent public key creation
NAME="trezor_demo"  # will be used as GPG user id and public key name

echo "Hello GPG World!" > EXAMPLE
# Create, sign and export the public key
trezor-gpg $NAME --time $CREATED -o $NAME.pub

# Install GPG v2.1 (modern) and import the public key
gpg2 --import $NAME.pub
gpg2 --list-keys $NAME
# gpg2 --edit-key $NAME trust  # optional: mark it as trusted

# Perform actual GPG signature using TREZOR device
trezor-gpg $NAME EXAMPLE

# Verify signature using GPG2 binary
gpg2 --verify EXAMPLE.sig
