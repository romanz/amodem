#!/bin/bash
if [[ "$*" == *"--verify"* ]]
then
	gpg2 $*  # verify using GPG2 (for ECDSA and EdDSA keys)
else
	python -m trezor_agent.gpg.git_wrapper $*  # sign using TREZOR
fi
