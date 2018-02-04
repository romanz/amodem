# Installation

Install the following packages (depending on your distribution):

## Install dependencies

### Debian

    $ apt update && apt upgrade
    $ apt install python-pip python-dev python-tk libusb-1.0-0-dev libudev-dev 

### Fedora/RedHat

    $ yum update
    $ yum install python-pip python-devel python-tk libusb-devel libudev-devel \
                  gcc redhat-rpm-config

### OpenSUSE

    $ zypper install python-pip python-devel python-tk libusb-1_0-devel libudev-devel

If you are using python3 or your system `pip` command points to `pip3.x`
(`/etc/alternatives/pip -> /usr/bin/pip3.6`) you will need to install these
dependencies instead:

    $ zypper install python3-pip python3-devel python3-tk libusb-1_0-devel libudev-devel

## Update setuptools and pip

Also, update Python packages before starting the installation:

    $ pip install -U setuptools pip

## Check device's firmware version

Make sure you are running the latest firmware version on your hardware device.
Currently the following firmware versions are supported:

 * [TREZOR](https://wallet.trezor.io/data/firmware/releases.json): `1.4.2+`
 * [KeepKey](https://github.com/keepkey/keepkey-firmware/releases): `3.0.17+`
 * [Ledger Nano S](https://github.com/LedgerHQ/blue-app-ssh-agent): `0.0.3+` (install [SSH/PGP Agent](https://www.ledgerwallet.com/images/apps/chrome-mngr-apps.png) app)

## TREZOR

Make sure that your `udev` rules are configured [correctly](https://doc.satoshilabs.com/trezor-user/settingupchromeonlinux.html#manual-configuration-of-udev-rules).
Then, install the latest [trezor_agent](https://pypi.python.org/pypi/trezor_agent) package:

    $ pip install trezor_agent

Or, directly from the latest source code:

    $ git clone https://github.com/romanz/trezor-agent
    $ pip install --user -e trezor-agent/agents/trezor

## KeepKey

Make sure that your `udev` rules are configured [correctly](https://support.keepkey.com/support/solutions/articles/6000037796-keepkey-wallet-is-not-being-recognized-by-linux).
Then, install the latest [keepkey_agent](https://pypi.python.org/pypi/keepkey_agent) package:

    $ pip install keepkey_agent

Or, directly from the latest source code:

    $ git clone https://github.com/romanz/trezor-agent
    $ pip install --user -e trezor-agent/agents/keepkey

## Ledger Nano S

Make sure that your `udev` rules are configured [correctly](https://ledger.zendesk.com/hc/en-us/articles/115005165269-What-if-Ledger-Wallet-is-not-recognized-on-Linux-).
Then, install the latest [ledger_agent](https://pypi.python.org/pypi/ledger_agent) package:

    $ pip install ledger_agent

Or, directly from the latest source code:

    $ git clone https://github.com/romanz/trezor-agent
    $ pip install --user -e trezor-agent/agents/ledger

## Troubleshooting

If there is an import problem with the installed `protobuf` package,
see [this issue](https://github.com/romanz/trezor-agent/issues/28) for fixing it.

If you can't find the command-line utilities (after running `pip install --user`),
please make sure that `~/.local/bin` is on your `PATH` variable
(see a [relevant](https://github.com/pypa/pip/issues/3813) issue).

If you can't find command-line utilities and are on macOS/OSX check `~/Library/Python/2.7/bin` and add to `PATH` if necessary (see a [relevant](https://github.com/romanz/trezor-agent/issues/155) issue).
