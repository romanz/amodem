#!/bin/bash
set -x
CREATED=1460731897  # needed for consistent public key creation
NAME="trezor_key"  # will be used as GPG user id and public key name

echo "Hello GPG World!" > EXAMPLE
./signer.py $NAME --time $CREATED --public-key --file EXAMPLE --verbose
./check.py $NAME.pub EXAMPLE.sig  # pure Python verification

# Install GPG v2.1 (modern) and verify the signature
gpg2 --import $NAME.pub
gpg2 --list-keys $NAME
# gpg2 --edit-key trezor_key trust  # optional: mark it as trusted
gpg2 --verify EXAMPLE.sig
