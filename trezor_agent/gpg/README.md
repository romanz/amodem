# Using TREZOR as hardware GPG agent

## Generate new GPG signing key:
First, verify that you have GPG 2.1+ [installed](https://gist.github.com/vt0r/a2f8c0bcb1400131ff51):
```
$ gpg2 --version | head -n1
gpg (GnuPG) 2.1.11
```
Update you TREZOR firmware to the latest version (at least [5430c82](https://github.com/trezor/trezor-mcu/commit/5430c82b2b1dbdd43c89de419ef92b754bed4c91)): see [a sample build log](https://gist.github.com/romanz/324c8e513abf5b5a452602ed648fa2cf).

Install the latest development version of `trezor-agent`:
```
$ pip install git+https://github.com/romanz/trezor-agent.git@master
```

Define your GPG user ID as an environment variable:
```
$ export TREZOR_GPG_USER_ID="John Doe <john@doe.bit>"
```

There are two ways to generate TREZOR-based GPG public keys, as described below.

### (1) create new GPG identity:
```
$ trezor-gpg create > identity.pub           # create new TREZOR-based GPG identity
$ gpg2 --import identity.pub                 # import into local GPG public keyring
$ gpg2 --list-keys                           # verify that the new identity is created correctly
$ gpg2 --edit "${TREZOR_GPG_USER_ID}" trust  # OPTIONAL: mark the key as trusted
```
[![asciicast](https://asciinema.org/a/44880.png)](https://asciinema.org/a/44880)

### (2) create new subkey for an existing GPG identity:
```
$ gpg2 --list-keys "${TREZOR_GPG_USER_ID}"   # make sure this identity already exists
$ trezor-gpg create --subkey > identity.pub  # create new TREZOR-based GPG subkey
$ gpg2 --import identity.pub                 # append it to an existing identity
$ gpg2 --list-keys "${TREZOR_GPG_USER_ID}"   # verify that the new subkey is added to keyring
```
[![subkey](https://asciinema.org/a/8t78s6pqo5yocisaiolqnjp63.png)](https://asciinema.org/a/8t78s6pqo5yocisaiolqnjp63)

## Generate GPG signatures using a TREZOR device:
```
$ trezor-gpg sign EXAMPLE                    # confirm signature using the device
$ gpg2 --verify EXAMPLE.asc                  # verify using standard GPG binary
```
[![sign](https://asciinema.org/a/f1unkptesb7anq09i8wugoko6.png)](https://asciinema.org/a/f1unkptesb7anq09i8wugoko6)

## Git commit & tag signatures:
Git can use GPG to sign and verify commits and tags (see [here](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)):
```
$ git config --local gpg.program "trezor-git-gpg-wrapper.sh"
$ git commit --gpg-sign                      # create GPG-signed commit
$ git log --show-signature -1                # verify commit signature
$ git tag --sign "TAG"                       # create GPG-signed tag
$ git verify-tag "TAG"                       # verify tag signature
```
[![asciicast](https://asciinema.org/a/44879.png)](https://asciinema.org/a/44879)
