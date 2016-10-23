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

# Quickstart

[![asciicast](https://asciinema.org/a/88teiuljlxp8w0avvn7oorr4s.png)](https://asciinema.org/a/88teiuljlxp8w0avvn7oorr4s)

# Initialization
```
$ ./scripts/gpg-init "John Doe <john@doe.bit>"
2016-10-22 22:36:23,952 INFO         creating new ed25519 GPG primary key for "John Doe <john@doe.bit>"                                   [__main__.py:56]
2016-10-22 22:36:23,952 INFO         please confirm GPG signature on Trezor for "John Doe <john@doe.bit>"...                              [device.py:39]
2016-10-22 22:36:26,307 INFO         please confirm GPG signature on Trezor for "John Doe <john@doe.bit>"...                              [device.py:39]
gpg: keybox '/home/roman/.gnupg/trezor/pubring.kbx' created
gpg: /home/roman/.gnupg/trezor/trustdb.gpg: trustdb created
gpg: key 7482BAFD9AFE0C94: public key "John Doe <john@doe.bit>" imported
gpg: Total number processed: 1
gpg:               imported: 1
Marking 0x7482BAFD9AFE0C94 as trusted...
```

# Usage examples:

## Start the TREZOR-based gpg-agent:
```
$ ./scripts/gpg-shell
gpg: key 7482BAFD9AFE0C94 marked as ultimately trusted
gpg: checking the trustdb
gpg: marginals needed: 3  completes needed: 1  trust model: pgp
gpg: depth: 0  valid:   1  signed:   0  trust: 0-, 0q, 0n, 0m, 0f, 1u
/home/roman/.gnupg/trezor/pubring.kbx
-------------------------------------
pub   ed25519 2016-10-22 [SC]
      74D5CDA3387022810BC97B257482BAFD9AFE0C94
      Keygrip = 78DDB30A6A9A7573606BAEDDC0D4065610831B6B
uid           [ultimate] John Doe <john@doe.bit>
sub   cv25519 2016-10-22 [E]
      Keygrip = 182A7F215C98CA29CF8A8A92B92D4A4F8BBEE1FD

Starting GPG-enabled shell...
```

Note: this agent intercepts all GPG requests in the current shell, and will be killed after this shell is closed.

## Sign and verify GPG messages:
```
$ echo "Hello World!" | gpg2 --sign | gpg2 --verify
2016-10-22 22:36:38,088 INFO         please confirm GPG signature on Trezor for "John Doe <john@doe.bit>"...                              [device.py:39]
gpg: Signature made Sat 22 Oct 2016 10:36:37 PM IDT
gpg:                using EDDSA key 7482BAFD9AFE0C94
gpg: Good signature from "John Doe <john@doe.bit>" [ultimate]
```
## Encrypt and decrypt GPG messages:
```
$ date | gpg2 --encrypt -r John | gpg2 --decrypt
2016-10-22 22:36:43,820 INFO         please confirm GPG decryption on Trezor for "John Doe <john@doe.bit>"...                             [device.py:52]
gpg: encrypted with 256-bit ECDH key, ID 4BE3A7CA55CEB3DE, created 2016-10-22
      "John Doe <john@doe.bit>"
Sat Oct 22 22:36:43 IDT 2016
```

## Git commit & tag signatures:
Git can use GPG to sign and verify commits and tags (see [here](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)):
```
$ git config --local gpg.program gpg2
$ git commit --gpg-sign                      # create GPG-signed commit
$ git log --show-signature -1                # verify commit signature
$ git tag --sign "v1.2.3"                    # create GPG-signed tag
$ git verify-tag "v1.2.3"                    # verify tag signature
```
