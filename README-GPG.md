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

## Identity creation
[![asciicast](https://asciinema.org/a/c2yodst21h9obttkn9wgf3783.png)](https://asciinema.org/a/c2yodst21h9obttkn9wgf3783)

## Sample usage (signature and decryption)
[![asciicast](https://asciinema.org/a/7x0h9tyoyu5ar6jc8y9oih0ba.png)](https://asciinema.org/a/7x0h9tyoyu5ar6jc8y9oih0ba)

You can use GNU Privacy Assistant (GPA) in order to inspect the created keys
and perform signature and decryption operations using:

```
$ sudo apt install gpa
$ ./scripts/gpg-shell gpa
```
[![GPA](https://cloud.githubusercontent.com/assets/9900/20224804/053d7474-a849-11e6-87f3-ab07dc536158.png)](https://www.gnupg.org/related_software/swlist.html#gpa)

## Git commit & tag signatures:
Git can use GPG to sign and verify commits and tags (see [here](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)):
```
$ git config --local gpg.program $(which gpg2)
$ git commit --gpg-sign                      # create GPG-signed commit
$ git log --show-signature -1                # verify commit signature
$ git tag --sign "v1.2.3"                    # create GPG-signed tag
$ git verify-tag "v1.2.3"                    # verify tag signature
```
