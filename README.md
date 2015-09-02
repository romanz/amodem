# Using Trezor as a hardware SSH agent

[![Build Status](https://travis-ci.org/romanz/trezor-agent.svg?branch=master)](https://travis-ci.org/romanz/trezor-agent)

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

	/tmp $ trezor-agent ssh.hostname.com -v > hostname.pub

Append `hostname.pub` contents to `~/.ssh/authorized_keys`
configuration file at `ssh.hostname.com`, so the remote server
would allow you to login using the corresponding private key signature.

## Usage

Run:

	/tmp $ trezor-agent ssh.hostname.com -v -c
	2015-09-02 15:09:39,782 INFO         getting "ssh://localhost" public key from Trezor...
	2015-09-02 15:09:44,430 INFO         please confirm user "roman" login to "ssh://localhost" using Trezor...
	2015-09-02 15:09:46,152 INFO         signature status: OK
	Linux lmde 3.16.0-4-amd64 #1 SMP Debian 3.16.7-ckt11-1+deb8u3 (2015-08-04) x86_64

	The programs included with the Debian GNU/Linux system are free software;
	the exact distribution terms for each program are described in the
	individual files in /usr/share/doc/*/copyright.

	Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
	permitted by applicable law.
	Last login: Tue Sep  1 15:57:05 2015 from localhost
	~ $

Make sure to confirm SSH signature on the Trezor device when requested.
