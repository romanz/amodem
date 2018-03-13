# Hardware-based SSH/GPG agent

[![Build Status](https://travis-ci.org/romanz/trezor-agent.svg?branch=master)](https://travis-ci.org/romanz/trezor-agent)
[![Chat](https://badges.gitter.im/romanz/trezor-agent.svg)](https://gitter.im/romanz/trezor-agent)

This project allows you to use various hardware security devices to operate GPG and SSH.  Instead of keeping your key on your computer and decrypting it with a passphrase when you want to use it, the key is generated and stored on the device and never reaches your computer.  Read more about the design [here](doc/DESIGN.md).

You can do things like sign your emails, git commits, and software packages, manage your passwords (with [pass](https://www.passwordstore.org/) and [gopass](https://www.justwatch.com/gopass/), among others), authenticate web tunnels and file transfers, and more.

See SatoshiLabs' blog posts about this feature:

- [TREZOR Firmware 1.3.4 enables SSH login](https://medium.com/@satoshilabs/trezor-firmware-1-3-4-enables-ssh-login-86a622d7e609)
- [TREZOR Firmware 1.3.6 — GPG Signing, SSH Login Updates and Advanced Transaction Features for Segwit](https://medium.com/@satoshilabs/trezor-firmware-1-3-6-20a7df6e692)
- [TREZOR Firmware 1.4.0 — GPG decryption support](https://www.reddit.com/r/TREZOR/comments/50h8r9/new_trezor_firmware_fidou2f_and_initial_ethereum/d7420q7/)

Currently [TREZOR One](https://trezor.io/), [TREZOR Model T](https://trezor.io/), [Keepkey](https://www.keepkey.com/), and [Ledger Nano S](https://www.ledgerwallet.com/products/ledger-nano-s) are supported.

## Documentation

* **Installation** instructions are [here](doc/INSTALL.md)
* **SSH** instructions and common use cases are [here](doc/README-SSH.md)

    Note: If you're using Windows, see [trezor-ssh-agent](https://github.com/martin-lizner/trezor-ssh-agent) by Martin Lízner.

* **GPG** instructions and common use cases are [here](doc/README-GPG.md)
* Instructions to configure a Trezor-style **PIN entry** program are [here](doc/README-PINENTRY.md)