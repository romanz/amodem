Note: the GPG-related code is still under development, so please try the current implementation
and please let me [know](https://github.com/romanz/trezor-agent/issues/new) if something doesn't
work well for you. If possible:

 * record the session (e.g. using [asciinema](https://asciinema.org))
 * attach the GPG agent log from `~/.gnupg/{trezor,ledger}/gpg-agent.log`

Thanks!

# Installation

First, verify that you have GPG 2.1.11+ installed
([Debian](https://gist.github.com/vt0r/a2f8c0bcb1400131ff51),
[macOS](https://sourceforge.net/p/gpgosx/docu/Download/)):

```
$ gpg2 --version | head -n1
gpg (GnuPG) 2.1.15
```

This GPG version is included in [Ubuntu 16.04](https://launchpad.net/ubuntu/+source/gnupg2)
and [Linux Mint 18](https://community.linuxmint.com/software/view/gnupg2).

Update you device firmware to the latest version and install your specific `agent` package:

```
$ pip install --user (trezor|keepkey|ledger)_agent
```

# Quickstart

## Identity creation
[![asciicast](https://asciinema.org/a/3iNw2L9QWB8R3EVdYdAxMOLK8.png)](https://asciinema.org/a/3iNw2L9QWB8R3EVdYdAxMOLK8)

In order to use specific device type for GPG indentity creation, use either command:
```
$ trezor-gpg init "Roman Zeyde <roman.zeyde@gmail.com>"
$ ledger-gpg init "Roman Zeyde <roman.zeyde@gmail.com>"
```

## Sample usage (signature and decryption)
[![asciicast](https://asciinema.org/a/120441.png)](https://asciinema.org/a/120441)

In order to use specific device type for GPG operations, set the following environment variable to either:
```
$ export GNUPGHOME=~/.gnupg/{trezor,ledger}
```

You can use GNU Privacy Assistant (GPA) in order to inspect the created keys
and perform signature and decryption operations using:

```
$ sudo apt install gpa
$ GNUPGHOME=~/.gnupg/trezor gpa
```
[![GPA](https://cloud.githubusercontent.com/assets/9900/20224804/053d7474-a849-11e6-87f3-ab07dc536158.png)](https://www.gnupg.org/related_software/swlist.html#gpa)

## Git commit & tag signatures:
Git can use GPG to sign and verify commits and tags (see [here](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)):
```
$ git config --local commit.gpgsign 1
$ git config --local gpg.program $(which gpg2)
$ git commit --gpg-sign                      # create GPG-signed commit
$ git log --show-signature -1                # verify commit signature
$ git tag v1.2.3 --sign                      # create GPG-signed tag
$ git tag v1.2.3 --verify                    # verify tag signature
```

## Password manager

First install `pass` from [passwordstore.org](https://www.passwordstore.org/) and initialize it to use your TREZOR-based GPG identity:
```
$ export GNUPGHOME=~/.gnupg/trezor
$ pass init "Roman Zeyde <roman.zeyde@gmail.com>"
Password store initialized for Roman Zeyde <roman.zeyde@gmail.com>
```
Then, you can generate truly random passwords and save them encrypted using your public key (as separate `.gpg` files under `~/.password-store/`):
```
$ pass generate Dev/github 32
$ pass generate Social/hackernews 32
$ pass generate Social/twitter 32
$ pass generate VPS/linode 32
$ pass
Password Store
├── Dev
│   └── github
├── Social
│   ├── hackernews
│   └── twitter
└── VPS
    └── linode
```
In order to paste them into the browser, you'd need to decrypt the password using your hardware device:
```
$ pass --clip VPS/linode
Copied VPS/linode to clipboard. Will clear in 45 seconds.
```

You can also use the following [Qt-based UI](https://qtpass.org/) for `pass`:
```
$ sudo apt install qtpass
$ GNUPGHOME=~/.gnupg/trezor qtpass
```

## Re-generation of an existing GPG identity
[![asciicast](https://asciinema.org/a/5tIQa5qt5bV134oeOqFyKEU29.png)](https://asciinema.org/a/5tIQa5qt5bV134oeOqFyKEU29)

If you've forgotten the timestamp value, but still have access to the public key, then you can
retrieve the timestamp with the following command (substitute "john@doe.bit" for the key's address or id):

```
$ gpg2 --export 'john@doe.bit' | gpg2 --list-packets | grep created | head -n1
```

## Adding new user IDs

After your main identity is created, you can add new user IDs using the regular GnuPG commands:
```
$ trezor-gpg init "Foobar" -vv
$ export GNUPGHOME=${HOME}/.gnupg/trezor
$ gpg2 -K
------------------------------------------
sec   nistp256/6275E7DA 2017-12-05 [SC]
uid         [ultimate] Foobar
ssb   nistp256/35F58F26 2017-12-05 [E]

$ gpg2 --edit Foobar
gpg> adduid
Real name: Xyzzy
Email address:
Comment:
You selected this USER-ID:
    "Xyzzy"

Change (N)ame, (C)omment, (E)mail or (O)kay/(Q)uit? o

gpg> save

$ gpg2 -K
------------------------------------------
sec   nistp256/6275E7DA 2017-12-05 [SC]
uid         [ultimate] Xyzzy
uid         [ultimate] Foobar
ssb   nistp256/35F58F26 2017-12-05 [E]
```

## GnuPG subkey generation
In order to add TREZOR-based subkey to an existing GnuPG identity, use the `--subkey` flag:
```
$ gpg2 -k foobar
pub   rsa2048/90C4064B 2017-10-10 [SC]
uid         [ultimate] foobar
sub   rsa2048/4DD05FF0 2017-10-10 [E]

$ trezor-gpg init "foobar" --subkey
```

[![asciicast](https://asciinema.org/a/Ick5G724zrZRFsGY7ZUdFSnV1.png)](https://asciinema.org/a/Ick5G724zrZRFsGY7ZUdFSnV1)

In order to enter existing GPG passphrase, I recommend installing and using a graphical Pinentry:
```
$ sudo apt install pinentry-gnome3
$ sudo update-alternatives --config pinentry
There are 4 choices for the alternative pinentry (providing /usr/bin/pinentry).

  Selection    Path                      Priority   Status
------------------------------------------------------------
* 0            /usr/bin/pinentry-gnome3   90        auto mode
  1            /usr/bin/pinentry-curses   50        manual mode
  2            /usr/bin/pinentry-gnome3   90        manual mode
  3            /usr/bin/pinentry-qt       80        manual mode
  4            /usr/bin/pinentry-tty      30        manual mode

Press <enter> to keep the current choice[*], or type selection number: 0
```
