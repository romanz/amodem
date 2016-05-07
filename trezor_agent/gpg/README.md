# Using TREZOR as hardware GPG agent

## Generate new GPG signing key:
```
$ export TREZOR_GPG_USER_ID="Satoshi Nakamoto <satoshi@nakamoto.bit>"
```

### Create new GPG identity:
```
$ trezor-gpg create > identity.pub                  # create new TREZOR-based GPG identity
$ gpg2 --import identity.pub                        # import into local GPG public keyring
$ gpg2 --edit "${TREZOR_GPG_USER_ID}" trust         # OPTIONAL: mark the key as trusted
```

### Create new subkey for an existing GPG identity:
```
$ gpg2 --list-keys "${TREZOR_GPG_USER_ID}"          # make sure this identity already exists
$ trezor-gpg create --subkey > identity.pub         # create new TREZOR-based GPG public key
$ gpg2 --import identity.pub                        # append it to existing identity
```

## Generate GPG signatures using a TREZOR device:
```
$ trezor-gpg sign EXAMPLE                           # confirm signature using the device
$ gpg2 --verify EXAMPLE.asc                         # verify using standard GPG binary
```

## Git commit/tag signature:
```
$ git config --local gpg.program "trezor-git-gpg-wrapper.sh"
$ git commit --gpg-sign                             # create GPG-signed commit
$ git log --show-signature                          # verify commits' signatures
$ git tag --sign "TAG"                              # create GPG-signed tag
$ git verify-tag "TAG"                              # verify tag signature
```