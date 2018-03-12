# Installation

## 1. Prerequisites

Install the following packages (depending on your distribution):

### OS dependencies

This software needs Python, libusb, and libudev along with development files.

You can install them on these distributions as follows:

##### Debian

    $ apt-get install python3-pip python3-dev python3-tk libusb-1.0-0-dev libudev-dev

##### Fedora/RedHat

    $ yum install python3-pip python3-devel python3-tk libusb-devel libudev-devel \
                  gcc redhat-rpm-config

##### OpenSUSE

    $ zypper install python-pip python-devel python-tk libusb-1_0-devel libudev-devel

If you are using python3 or your system `pip` command points to `pip3.x`
(`/etc/alternatives/pip -> /usr/bin/pip3.6`) you will need to install these
dependencies instead:

    $ zypper install python3-pip python3-devel python3-tk libusb-1_0-devel libudev-devel

### GPG

If you intend to use GPG make sure you have GPG installed and up to date.  This software requires a GPG version >= 2.1.11.

You can verify your installed version by running:
```
$ gpg2 --version | head -n1
gpg (GnuPG) 2.1.15
```

 * Follow this installation guide for [Debian](https://gist.github.com/vt0r/a2f8c0bcb1400131ff51)
 * Install GPG for [macOS](https://sourceforge.net/p/gpgosx/docu/Download/)
 * Install packages for Ubuntu 16.04 [here](https://launchpad.net/ubuntu/+source/gnupg2)
 * Install packages for Linux Mint 18 [here](https://community.linuxmint.com/software/view/gnupg2)

# 2. Install the TREZOR agent

1. Make sure you are running the latest firmware version on your Trezor:

 * [TREZOR firmware releases](https://wallet.trezor.io/data/firmware/releases.json): `1.4.2+`

2. Make sure that your `udev` rules are configured [correctly](https://doc.satoshilabs.com/trezor-user/settingupchromeonlinux.html#manual-configuration-of-udev-rules).

3. Then, install the latest [trezor_agent](https://pypi.python.org/pypi/trezor_agent) package:

    ```
    $ pip3 install trezor_agent
    ```

    Or, directly from the latest source code:

    ```
    $ git clone https://github.com/romanz/trezor-agent
    $ pip3 install --user -e trezor-agent/agents/trezor
    ```

# 3. Install the KeepKey agent

1. Make sure you are running the latest firmware version on your KeepKey:

 * [KeepKey firmware releases](https://github.com/keepkey/keepkey-firmware/releases): `3.0.17+`

2. Make sure that your `udev` rules are configured [correctly](https://support.keepkey.com/support/solutions/articles/6000037796-keepkey-wallet-is-not-being-recognized-by-linux).
Then, install the latest [keepkey_agent](https://pypi.python.org/pypi/keepkey_agent) package:

    ```
    $ pip3 install keepkey_agent
    ```

    Or, directly from the latest source code:

    ```
    $ git clone https://github.com/romanz/trezor-agent
    $ pip3 install --user -e trezor-agent/agents/keepkey
    ```

# 4. Install the Ledger Nano S agent

1. Make sure you are running the latest firmware version on your Ledger Nano S:

 * [Ledger Nano S firmware releases](https://github.com/LedgerHQ/blue-app-ssh-agent): `0.0.3+` (install [SSH/PGP Agent](https://www.ledgerwallet.com/images/apps/chrome-mngr-apps.png) app)

2. Make sure that your `udev` rules are configured [correctly](https://ledger.zendesk.com/hc/en-us/articles/115005165269-What-if-Ledger-Wallet-is-not-recognized-on-Linux-).
3. Then, install the latest [ledger_agent](https://pypi.python.org/pypi/ledger_agent) package:

    ```
    $ pip3 install ledger_agent
    ```

    Or, directly from the latest source code:

    ```
    $ git clone https://github.com/romanz/trezor-agent
    $ pip3 install --user -e trezor-agent/agents/ledger
    ```

# 5. Installation Troubleshooting

If there is an import problem with the installed `protobuf` package,
see [this issue](https://github.com/romanz/trezor-agent/issues/28) for fixing it.

If you can't find the command-line utilities (after running `pip install --user`),
please make sure that `~/.local/bin` is on your `PATH` variable
(see a [relevant](https://github.com/pypa/pip/issues/3813) issue).

If you can't find command-line utilities and are on macOS/OSX check `~/Library/Python/2.7/bin` and add to `PATH` if necessary (see a [relevant](https://github.com/romanz/trezor-agent/issues/155) issue).
