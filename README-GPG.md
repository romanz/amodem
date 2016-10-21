Note: the GPG-related code is still under development, so please try the current implementation
and feel free to [report any issue](https://github.com/romanz/trezor-agent/issues) you have encountered.
Thanks!

# Installation

First, verify that you have GPG 2.1+ [installed](https://gist.github.com/vt0r/a2f8c0bcb1400131ff51):

```
$ gpg2 --version | head -n1
gpg (GnuPG) 2.1.15
```

Update you TREZOR firmware to the latest version (at least v1.4.0).

Install latest `trezor-agent` package from GitHub:
```
$ pip install --user git+https://github.com/romanz/trezor-agent.git
```

Define your GPG user ID as an environment variable:
```
$ TREZOR_GPG_USER_ID="John Doe <john@doe.bit>"
```

There are two ways to generate TREZOR-based GPG public keys, as described below.

## 1. generate a new GPG identity:

```
$ trezor-gpg create "${TREZOR_GPG_USER_ID}" | gpg2 --import           # use the TREZOR to confirm signing the primary key
gpg: key 5E4D684D: public key "John Doe <john@doe.bit>" imported
gpg: Total number processed: 1
gpg:               imported: 1

$ gpg2 --edit "${TREZOR_GPG_USER_ID}" trust                           # set this key to ultimate trust (option #5)

$ gpg2 -k
/home/roman/.gnupg/pubring.kbx
------------------------------
pub   nistp256/5E4D684D 2016-06-17 [SC]
uid         [ultimate] John Doe <john@doe.bit>
sub   nistp256/A31D9E25 2016-06-17 [E]
```

## 2. generate a new subkey for an existing GPG identity:

```
$ gpg2 -k                                                             # suppose there is already a GPG primary key
/home/roman/.gnupg/pubring.kbx
------------------------------
pub   rsa2048/87BB07B4 2016-06-17 [SC]
uid         [ultimate] John Doe <john@doe.bit>
sub   rsa2048/7176D31F 2016-06-17 [E]

$ trezor-gpg create "${TREZOR_GPG_USER_ID}" | gpg2 --import           # use the TREZOR to confirm signing the subkey
gpg: key 87BB07B4: "John Doe <john@doe.bit>" 2 new signatures
gpg: key 87BB07B4: "John Doe <john@doe.bit>" 2 new subkeys
gpg: Total number processed: 1
gpg:            new subkeys: 2
gpg:         new signatures: 2

$ gpg2 -k
/home/roman/.gnupg/pubring.kbx
------------------------------
pub   rsa2048/87BB07B4 2016-06-17 [SC]
uid         [ultimate] John Doe <john@doe.bit>
sub   rsa2048/7176D31F 2016-06-17 [E]
sub   nistp256/DDE80B36 2016-06-17 [S]
sub   nistp256/E3D0BA19 2016-06-17 [E]
```

# Usage examples:

## Start the TREZOR-based gpg-agent:
```
$ trezor-gpg agent &
```
Note: this agent intercepts all GPG requests, so make sure to close it (e.g. by using `killall trezor-gpg`),
when you are done with the TREZOR-based GPG operations.

## Sign and verify GPG messages:
```
$ echo "Hello World!" | gpg2 --sign | gpg2 --verify
gpg: Signature made Fri 17 Jun 2016 08:55:13 PM IDT using ECDSA key ID 5E4D684D
gpg: Good signature from "John Doe <john@doe.bit>" [ultimate]
```
## Encrypt and decrypt GPG messages:
```
$ date | gpg2 --encrypt -r "${TREZOR_GPG_USER_ID}" | gpg2 --decrypt
gpg: encrypted with 256-bit ECDH key, ID A31D9E25, created 2016-06-17
      "John Doe <john@doe.bit>"
Fri Jun 17 20:55:31 IDT 2016
```

## Git commit & tag signatures:
Git can use GPG to sign and verify commits and tags (see [here](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)):
```
$ git config --local gpg.program gpg2
$ git commit --gpg-sign                      # create GPG-signed commit
$ git log --show-signature -1                # verify commit signature
$ git tag --sign "TAG"                       # create GPG-signed tag
$ git verify-tag "TAG"                       # verify tag signature
```
