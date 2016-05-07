# Using TREZOR as hardware GPG agent

## Generate new GPG signing key:
```
$ export TREZOR_GPG_USER_ID="John Doe <john@doe.bit>"
```

### Create new GPG identity:
```
$ trezor-gpg create > identity.pub                  # create new TREZOR-based GPG identity
2016-05-07 13:05:30,380 INFO       nist256p1 GPG public key <976C7E8C5BF0EB2A> created at 2016-05-07 13:05:30 for "John Doe <john@doe.bit>"
2016-05-07 13:05:30,380 INFO       signing public key "John Doe <john@doe.bit>"
2016-05-07 13:05:30,381 INFO       signing digest: 32D9A9C5E6B39819A84B1B735FD7BB224E599D06AFCB1CD012992E5F2A7BEF2D

$ gpg2 --import identity.pub                        # import into local GPG public keyring
gpg: key 5BF0EB2A: public key "John Doe <john@doe.bit>" imported
gpg: Total number processed: 1
gpg:               imported: 1

$ gpg2 -k                                           # verify that the new identity is created correctly
pub   nistp256/2576C1EF 2016-05-07 [SC]
uid         [ unknown] John Doe <john@doe.bit>

$ gpg2 --edit "${TREZOR_GPG_USER_ID}" trust         # OPTIONAL: mark the key as trusted
```

### Create new subkey for an existing GPG identity:
```
$ gpg2 --list-keys "${TREZOR_GPG_USER_ID}"          # make sure this identity already exists
pub   rsa2048/39ADCBA2 2016-05-07 [SC]
uid         [ultimate] John Doe <john@doe.bit>
sub   rsa2048/0F1AA6CA 2016-05-07 [E]

$ trezor-gpg create --subkey > identity.pub         # create new TREZOR-based GPG public key
2016-05-07 13:09:53,097 INFO       nist256p1 GPG public key <302CE72CAF4A5DD7> created at 2016-05-07 13:09:52 for "John Doe <john@doe.bit>"
2016-05-07 13:09:53,102 INFO       adding subkey to primary GPG key "John Doe <john@doe.bit>" (FC527CB939ADCBA2)
2016-05-07 13:09:53,102 INFO       confirm signing subkey with hardware device
2016-05-07 13:09:53,103 INFO       signing digest: C8686DF576AB3AC13F0CD65F1D3F9575709A56598849CE43882C2609F861FE29
2016-05-07 13:09:56,305 INFO       confirm signing subkey with gpg-agent
2016-05-07 13:09:56,323 INFO       signing digest: CB02710AB6554D0D2734D2BEDAC0D914D2402644EE2C8E5F68422F6B71A22248

$ gpg2 --import identity.pub                        # append it to existing identity
gpg: key 39ADCBA2: "John Doe <john@doe.bit>" 1 new signature
gpg: key 39ADCBA2: "John Doe <john@doe.bit>" 1 new subkey
gpg: Total number processed: 1
gpg:            new subkeys: 1
gpg:         new signatures: 1

$ gpg2 --list-keys "${TREZOR_GPG_USER_ID}"          # verify that the new subkey is added to existing keyring
pub   rsa2048/39ADCBA2 2016-05-07 [SC]
uid         [ultimate] John Doe <john@doe.bit>
sub   rsa2048/0F1AA6CA 2016-05-07 [E]
sub   nistp256/AF4A5DD7 2016-05-07 [S]
```

## Generate GPG signatures using a TREZOR device:
```
$ trezor-gpg sign EXAMPLE                           # confirm signature using the device
2016-05-07 13:06:35,464 INFO       nist256p1 GPG public key <976C7E8C5BF0EB2A> created at 2016-05-07 13:05:30 for "John Doe <john@doe.bit>"
2016-05-07 13:06:35,464 INFO       signing 7 byte message at 2016-05-07 13:06:35
2016-05-07 13:06:35,464 INFO       signing digest: A0D6CD4FA3AC68FED14EA8B4A712F4EA06426655911067C85FCB087F19043114

$ gpg2 --verify EXAMPLE.asc                         # verify using standard GPG binary
gpg: assuming signed data in 'EXAMPLE'
gpg: Signature made Sat 07 May 2016 01:06:35 PM IDT using ECDSA key ID 5BF0EB2A
gpg: Good signature from "John Doe <john@doe.bit>" [ultimate]
```

## Git commit/tag signature:
```
$ git config --local gpg.program "trezor-git-gpg-wrapper.sh"
$ git commit --gpg-sign                             # create GPG-signed commit
$ git log --show-signature                          # verify commits' signatures
$ git tag --sign "TAG"                              # create GPG-signed tag
$ git verify-tag "TAG"                              # verify tag signature
```