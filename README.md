# Using Trezor as a hardware SSH agent

## Screencast demo usage

[![Demo](https://asciinema.org/a/22959.png)](https://asciinema.org/a/22959)

## Installation

First, make sure that the latest `trezorlib` Python package
is installed correctly:

	$ pip install Cython trezor

Then, install the latest `trezor_agent` package:

	$ pip install trezor_agent

## Public key generation

Run:

	$ trezor-agent ssh.hostname.com -v > hostname.pub

Append `hostname.pub` contents to `~/.ssh/authorized_keys`
configuration file at `ssh.hostname.com`, so the remote server
would allow you to login using the corresponding private key signature.

## Usage

Run:

	$ trezor-agent ssh.hostname.com -v -c

Make sure to confirm SSH signature on the Trezor device when requested.
