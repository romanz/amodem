# Generate new stand-along GPG identity

```
$ USER_ID="Satoshi Nakamoto <satoshi@nakamoto.bit>"
$ trezor-gpg create "${USER_ID}" > identity.pub           # create new TREZOR-based GPG identity
$ gpg2 --import identity.pub                              # import into local GPG public keyring
$ gpg2 --edit "${USER_ID}" trust                          # OPTIONAL: mark the key as trusted
```

# Generate new subkey for existing GPG identity
```
$ USER_ID="Satoshi Nakamoto <satoshi@nakamoto.bit>"
$ gpg2 --list-keys "${USER_ID}"                           # make sure this identity already exists
$ trezor-gpg create --subkey "${USER_ID}" > identity.pub  # create new TREZOR-based GPG public key
$ gpg2 --import identity.pub                              # append it to existing identity
```

# Generate signatures using the TREZOR device
```
$ trezor-gpg sign EXAMPLE > EXAMPLE.sig					  # confirm signature using the device
$ gpg2 --verify EXAMPLE.sig                               # verify using standard GPG binary
```
