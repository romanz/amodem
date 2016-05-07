# Generate new GPG signing key:
```
$ export TREZOR_GPG_USER_ID="Satoshi Nakamoto <satoshi@nakamoto.bit>"
```

## Create new GPG identity:
```
$ trezor-gpg create > identity.pub                  # create new TREZOR-based GPG identity
$ gpg2 --import identity.pub                        # import into local GPG public keyring
$ gpg2 --edit "${TREZOR_GPG_USER_ID}" trust         # OPTIONAL: mark the key as trusted
```

## Create new subkey for an existing GPG identity:
```
$ gpg2 --list-keys "${TREZOR_GPG_USER_ID}"          # make sure this identity already exists
$ trezor-gpg create --subkey > identity.pub         # create new TREZOR-based GPG public key
$ gpg2 --import identity.pub                        # append it to existing identity
```

# Generate GPG signatures using a TREZOR device:
```
$ trezor-gpg sign EXAMPLE                           # confirm signature using the device
$ gpg2 --verify EXAMPLE.asc                         # verify using standard GPG binary
```
