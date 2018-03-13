# GPG Agent

Note: the GPG-related code is still under development, so please try the current implementation
and please let me [know](https://github.com/romanz/trezor-agent/issues/new) if something doesn't
work well for you. If possible:

 * record the session (e.g. using [asciinema](https://asciinema.org))
 * attach the GPG agent log from `~/.gnupg/{trezor,ledger}/gpg-agent.log` (can be [encrypted](https://keybase.io/romanz))

Thanks!

## 1. Configuration

1. Initialize the agent GPG directory.

    [![asciicast](https://asciinema.org/a/3iNw2L9QWB8R3EVdYdAxMOLK8.png)](https://asciinema.org/a/3iNw2L9QWB8R3EVdYdAxMOLK8)

    Run

    ```
    $ (trezor|keepkey|ledger)-gpg init "Roman Zeyde <roman.zeyde@gmail.com>"
    ```

    Follow the instructions provided to complete the setup.  Keep note of the timestamp value which you'll need if you want to regenerate the key later.

    If you'd like a Trezor-style PIN entry program, follow [these instructions](README-PINENTRY.md).

2. Add `export GNUPGHOME=~/.gnupg/(trezor|keepkey|ledger)` to your `.bashrc` or other environment file.

    This `GNUPGHOME` contains your hardware keyring and agent settings.  This agent software assumes all keys are backed by hardware devices so you can't use standard GPG keys in `GNUPGHOME` (if you do mix keys you'll receive an error when you attempt to use them).

    If you wish to switch back to your software keys unset `GNUPGHOME`.

3. Log out and back into your session to ensure your environment is updated everywhere.

## 2. Usage

You can use any GPG commands or software that uses GPG as usual and will be prompted to interact with your hardware device as necessary.  The agent is automatically started if it isn't running when you run any `gpg` command.

##### Restarting the agent

If you change settings or need to restart the agent for some other reason, simply kill it.  It will restart the next time GPG is invoked.

## 3. Common Use Cases

### Sign and decrypt files

[![asciicast](https://asciinema.org/a/120441.png)](https://asciinema.org/a/120441)

### Inspect GPG keys
You can use GNU Privacy Assistant (GPA) in order to inspect the created keys and perform signature and decryption operations as usual:

```
$ sudo apt install gpa
$ gpa
```

[![GPA](https://cloud.githubusercontent.com/assets/9900/20224804/053d7474-a849-11e6-87f3-ab07dc536158.png)](https://www.gnupg.org/related_software/swlist.html#gpa)

### Sign Git commits and tags

Git can use GPG to sign and verify commits and tags (see [here](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)):

```
$ git config --local commit.gpgsign 1
$ git config --local gpg.program $(which gpg2)
$ git commit --gpg-sign                      # create GPG-signed commit
$ git log --show-signature -1                # verify commit signature
$ git tag v1.2.3 --sign                      # create GPG-signed tag
$ git tag v1.2.3 --verify                    # verify tag signature
```

### Manage passwords

Password managers such as [pass](https://www.passwordstore.org/) and [gopass](https://www.justwatch.com/gopass/) rely on GPG for encryption so you can use your device with them too.

##### With `pass`:

First install `pass` from [passwordstore.org] and initialize it to use your TREZOR-based GPG identity:
```
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
```

### Re-generate a GPG identity
[![asciicast](https://asciinema.org/a/5tIQa5qt5bV134oeOqFyKEU29.png)](https://asciinema.org/a/5tIQa5qt5bV134oeOqFyKEU29)

If you've forgotten the timestamp value, but still have access to the public key, then you can
retrieve the timestamp with the following command (substitute "john@doe.bit" for the key's address or id):

```
$ gpg2 --export 'john@doe.bit' | gpg2 --list-packets | grep created | head -n1
```

### Add new UIDs to your identity

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

### Generate GnuPG subkeys
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

### Sign and decrypt email

Follow [these instructions](enigmail.md) to set up Enigmail in Thunderbird.

### Start the agent as a systemd unit

##### 1. Create these files in `~/.config/systemd/user`

Replace `trezor` with `keepkey` or `ledger` as required.

###### `trezor-gpg-agent.service`

````
[Unit]
Description=trezor-gpg-agent
Requires=trezor-gpg-agent.socket

[Service]
Type=Simple
Environment="GNUPGHOME=%h/.gnupg/trezor"
Environment="PATH=/bin:/usr/bin:/usr/local/bin:%h/.local/bin"
ExecStart=/usr/bin/trezor-gpg-agent -vv
````

If you've installed `trezor-agent` locally you may have to change the path in `ExecStart=`.

###### `trezor-gpg-agent.socket`

````
[Unit]
Description=trezor-gpg-agent socket

[Socket]
ListenStream=%t/gnupg/S.gpg-agent
FileDescriptorName=std
SocketMode=0600
DirectoryMode=0700

[Install]
WantedBy=sockets.target
````

##### 2. Stop trezor-gpg-agent if it's already running

```
killall trezor-gpg-agent
```

##### 3. Run

```
systemctl --user start trezor-gpg-agent.service trezor-gpg-agent.socket
systemctl --user enable trezor-gpg-agent.socket
```
