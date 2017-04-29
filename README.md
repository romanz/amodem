# Using TREZOR as a hardware SSH/GPG agent

[![Build Status](https://travis-ci.org/romanz/trezor-agent.svg?branch=master)](https://travis-ci.org/romanz/trezor-agent)
[![Python Versions](https://img.shields.io/pypi/pyversions/trezor_agent.svg)](https://pypi.python.org/pypi/trezor_agent/)
[![Package Version](https://img.shields.io/pypi/v/trezor_agent.svg)](https://pypi.python.org/pypi/trezor_agent/)
[![Development Status](https://img.shields.io/pypi/status/trezor_agent.svg)](https://pypi.python.org/pypi/trezor_agent/)
[![Downloads](https://img.shields.io/pypi/dm/trezor_agent.svg)](https://pypi.python.org/pypi/trezor_agent/)

See SatoshiLabs' blog posts about this feature:

- [TREZOR Firmware 1.3.4 enables SSH login](https://medium.com/@satoshilabs/trezor-firmware-1-3-4-enables-ssh-login-86a622d7e609)
- [TREZOR Firmware 1.3.6 — GPG Signing, SSH Login Updates and Advanced Transaction Features for Segwit](https://medium.com/@satoshilabs/trezor-firmware-1-3-6-20a7df6e692)
- [TREZOR Firmware 1.4.0 — GPG decryption support](https://www.reddit.com/r/TREZOR/comments/50h8r9/new_trezor_firmware_fidou2f_and_initial_ethereum/d7420q7/)

## Installation

Install the following packages:

	$ apt-get install python-dev libusb-1.0-0-dev libudev-dev
	$ pip install -U setuptools pip

Make sure you are running the latest firmware version on your hardware device.
Currently the following firmware versions are supported:

 * [TREZOR](https://wallet.trezor.io/data/firmware/releases.json): `1.4.2+`
 * [KeepKey](https://github.com/keepkey/keepkey-firmware/releases): `3.0.17+`
 * [Ledger Nano S](https://github.com/LedgerHQ/blue-app-ssh-agent): `0.0.3+`

### TREZOR

Make sure that your `udev` rules are configured [correctly](https://doc.satoshilabs.com/trezor-user/settingupchromeonlinux.html#manual-configuration-of-udev-rules).
Then, install the latest [trezor_agent](https://pypi.python.org/pypi/trezor_agent) package:

	$ pip install trezor_agent

Or, directly from the latest source code:

	$ git clone https://github.com/romanz/trezor-agent
	$ pip install --user -e trezor-agent/agents/trezor

If you have an error regarding `protobuf` imports (after installing it), please see [this issue](https://github.com/romanz/trezor-agent/issues/28).

### KeepKey

Make sure that your `udev` rules are configured [correctly](https://support.keepkey.com/support/solutions/articles/6000037796-keepkey-wallet-is-not-being-recognized-by-linux).
Then, install the latest [keepkey_agent](https://pypi.python.org/pypi/keepkey_agent) package:

	$ pip install keepkey_agent

Or, directly from the latest source code:

	$ git clone https://github.com/romanz/trezor-agent
	$ pip install --user -e trezor-agent/agents/keepkey

### Ledger Nano S

Make sure that your `udev` rules are configured [correctly](http://support.ledgerwallet.com/knowledge_base/topics/ledger-wallet-is-not-recognized-on-linux).
Then, install the latest [ledger_agent](https://pypi.python.org/pypi/ledger_agent) package:

	$ pip install ledger_agent

Or, directly from the latest source code:

	$ git clone https://github.com/romanz/trezor-agent
	$ pip install --user -e trezor-agent/agents/ledger

## Usage

For SSH, see the [following instructions](README-SSH.md) (for Windows support,
see [trezor-ssh-agent](https://github.com/martin-lizner/trezor-ssh-agent) project (by Martin Lízner)).

For GPG, see the [following instructions](README-GPG.md).

See [here](https://github.com/romanz/python-trezor#pin-entering) for PIN entering instructions.

## Troubleshooting

If there is an import problem with the installed `protobuf` package,
see [this issue](https://github.com/romanz/trezor-agent/issues/28) for fixing it.

### Gitter

Questions, suggestions and discussions are welcome: [![Chat](https://badges.gitter.im/romanz/trezor-agent.svg)](https://gitter.im/romanz/trezor-agent)
