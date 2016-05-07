#!/bin/bash
if [[ "$*" == *"--verify"* ]]
then
	gpg2 $*  # verify using GPG2 (for ECDSA and EdDSA keys)
else
	trezor-gpg sign -o-  # sign using TREZOR and write the signature to stdout
fi
