# SSH Agent

## 1. Configuration

SSH requires no configuration, but you may put common command line options in `~/.ssh/agent.conf` to avoid repeating them in every invocation.

See `(trezor|keepkey|ledger|jade|onlykey)-agent -h` for details on supported options and the configuration file format.

If you'd like a Trezor-style PIN entry program, follow [these instructions](README-PINENTRY.md).

## 2. Usage

Use the `(trezor|keepkey|ledger|jade|onlykey)-agent` program to work with SSH. It has three main modes of operation:

##### 1. Export public keys

To get your public key so you can add it to `authorized_hosts` or allow
ssh access to a service that supports it, run:

```
(trezor|keepkey|ledger|jade|onlykey)-agent identity@myhost
```

The identity (ex: `identity@myhost`) is used to derive the public key and is added as a comment to the exported key string.

##### 2. Run a command with the agent's environment

Run

```
$ (trezor|keepkey|ledger|jade|onlykey)-agent identity@myhost -- COMMAND --WITH --ARGUMENTS
```

to start the agent in the background and execute the command with environment variables set up to use the SSH agent.  The specified identity is used for all SSH connections.  The agent will exit after the command completes.
Note the `--` separator, which is used to separate `trezor-agent`'s arguments from the SSH command arguments.

Example:
```
 (trezor|keepkey|ledger|jade|onlykey)-agent -e ed25519 bob@example.com -- rsync up/ bob@example.com:/home/bob
```

As a shortcut you can run

```
$ (trezor|keepkey|ledger|jade|onlykey)-agent identity@myhost -s
```

to start a shell with the proper environment.

##### 3. Connect to a server directly via `(trezor|keepkey|ledger|jade|onlykey)-agent`

If you just want to connect to a server this is the simplest way to do it:

```
$ (trezor|keepkey|ledger|jade|onlykey)-agent user@remotehost -c
```

The identity `user@remotehost` is used as both the destination user and host as well as for key derivation, so you must generate a separate key for each host you connect to.

## 3. Common Use Cases

### Start a single SSH session
[![Demo](https://asciinema.org/a/22959.png)](https://asciinema.org/a/22959)

### Start multiple SSH sessions from a sub-shell

This feature allows using regular SSH-related commands within a subprocess running user's shell.
`SSH_AUTH_SOCK` environment variable is defined for the subprocess (pointing to the SSH agent, running as a parent process).
This way the user can use SSH-related commands (e.g. `ssh`, `ssh-add`, `sshfs`, `git`, `hg`), while authenticating via the hardware device.

[![Subshell](https://asciinema.org/a/33240.png)](https://asciinema.org/a/33240)

### Load different SSH identities from configuration file

[![Config](https://asciinema.org/a/bdxxtgctk5syu56yfz8lcp7ny.png)](https://asciinema.org/a/bdxxtgctk5syu56yfz8lcp7ny)

### Implement passwordless login

Run:

	/tmp $ trezor-agent user@ssh.hostname.com -v > hostname.pub
	2015-09-02 15:03:18,929 INFO         getting "ssh://user@ssh.hostname.com" public key from Trezor...
	2015-09-02 15:03:23,342 INFO         disconnected from Trezor
	/tmp $ cat hostname.pub
	ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGSevcDwmT+QaZPUEWUUjTeZRBICChxMKuJ7dRpBSF8+qt+8S1GBK5Zj8Xicc8SHG/SE/EXKUL2UU3kcUzE7ADQ= ssh://user@ssh.hostname.com

Append `hostname.pub` contents to `/home/user/.ssh/authorized_keys`
configuration file at `ssh.hostname.com`, so the remote server
would allow you to login using the corresponding private key signature.

### Access remote Git/Mercurial repositories

Export your public key and register it in your repository web interface
(e.g. [GitHub](https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/)):

	$ trezor-agent -v -e ed25519 git@github.com > ~/.ssh/github.pub

Add the following configuration to your `~/.ssh/config` file:

	Host github.com
		IdentityFile ~/.ssh/github.pub

Use the following Bash alias for convenient Git operations:

	$ alias ssh-shell='trezor-agent ~/.ssh/github.pub -v --shell'

Now, you can use regular Git commands under the "SSH-enabled" sub-shell:

	$ ssh-shell
	$ git push origin master

The same works for Mercurial (e.g. on [BitBucket](https://confluence.atlassian.com/bitbucket/set-up-ssh-for-mercurial-728138122.html)):

	$ ssh-shell
	$ hg push

### Git commit signing

For more details, see the following great blog post: https://calebhearth.com/sign-git-with-ssh

	$ trezor-agent -e ed25519 user@host --shell
	$ ssh-add -L
	ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDeAmtnhHlyg4dzGP3/OF4WHX7NoYhClS98EK22q/O5+ <ssh://user@host|ed25519>
	$ git config --local user.signingkey "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDeAmtnhHlyg4dzGP3/OF4WHX7NoYhClS98EK22q/O5+"
	$ git config --local gpg.format ssh
	$ git config --local commit.gpgsign true

	$ git config --local gpg.ssh.allowedSignersFile $PWD/.git/allowed-signers
	$ echo "user@host ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDeAmtnhHlyg4dzGP3/OF4WHX7NoYhClS98EK22q/O5+" >> $PWD/.git/allowed-signers

	$ git commit --allow-empty --message="Testing SSH signing"
	[master 4a1f730] Testing SSH signing

	$ git log --show-signature -1
	commit 4a1f730d7f70fd31a0bda334734d0ac4dc9d97ad (HEAD -> master)
	Good "git" signature for user@host with ED25519 key SHA256:aESFjLsydJHQg1vnAkq42jQDkCcn4Tde4J+v+0XFmwM
	Author: Roman Zeyde <me@romanzey.de>
	Date:   Fri Oct 21 18:34:09 2022 +0300

	    Testing SSH signing

	$ cat .git/config
	[user]
		signingkey = ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDeAmtnhHlyg4dzGP3/OF4WHX7NoYhClS98EK22q/O5+
	[gpg]
		format = ssh
	[commit]
		gpgsign = true
	[gpg "ssh"]
		allowedSignersFile = /home/user/Code/test-git-ssh-sig/.git/allowed-signers


### Start the agent as a systemd unit

##### 1. Create these files in `~/.config/systemd/user`

Replace `trezor` with `keepkey` or `ledger` or `jade` or `onlykey` as required.

###### `trezor-ssh-agent.service`

````
[Unit]
Description=trezor-agent SSH agent
Requires=trezor-ssh-agent.socket

[Service]
Type=simple
Restart=always
Environment="DISPLAY=:0"
Environment="PATH=/bin:/usr/bin:/usr/local/bin:%h/.local/bin"
ExecStart=/usr/bin/trezor-agent --foreground --sock-path %t/trezor-agent/S.ssh IDENTITY
````

If you've installed `trezor-agent` locally you may have to change the path in `ExecStart=`.

Replace `IDENTITY` with the identity you used when exporting the public key.

`IDENTITY` can be a path (starting with `/`) to a file containing a list of public keys
generated by Trezor. I.e. `/home/myUser/.ssh/trezor.conf` with one public key per line.
This is a more convenient way to have a systemd setup that has to handle multiple
keys/hosts.

When updating the file, make sure to restart trezor-agent.

If you have multiple Trezors connected, you can select which one to use via a `TREZOR_PATH`
environment variable. Use `trezorctl list` to find the correct path. Then add it
to the agent with the following line:
````
Environment="TREZOR_PATH=<your path here>"
````
Note that USB paths depend on the _USB port_ which you use.

###### `trezor-ssh-agent.socket`

````
[Unit]
Description=trezor-agent SSH agent socket

[Socket]
ListenStream=%t/trezor-agent/S.ssh
FileDescriptorName=ssh
Service=trezor-ssh-agent.service
SocketMode=0600
DirectoryMode=0700

[Install]
WantedBy=sockets.target
````

##### 2. Run

```
systemctl --user start trezor-ssh-agent.service trezor-ssh-agent.socket
systemctl --user enable trezor-ssh-agent.socket
```

##### 3. Add this line to your `.bashrc` or equivalent file:

```bash
export SSH_AUTH_SOCK=$(systemctl show --user --property=Listen trezor-ssh-agent.socket | grep -o "/run.*" | cut -d " " -f 1)
```

Make sure the SSH_AUTH_SOCK variable matches the location of the socket that trezor-agent
is listening on: `ps -x | grep trezor-agent`. In this setup trezor-agent should start
automatically when the socket is opened.

##### 4. SSH will now automatically use your device key in all terminals.

## 5. Signatures with ssh and trezor

SSH and ssh-keygen can make and verify signatures, See
[ssh_signatures](https://www.agwa.name/blog/post/ssh_signatures)

See here for more ssh protocol details:
https://github.com/openssh/openssh-portable/blob/master/PROTOCOL.sshsig
https://github.com/openssh/openssh-portable/blob/master/sshsig.c
openssh/openssh-portable@2a9c9f7


##### generate SSH public key
```
$ trezor-agent -e ed25519 git@github.com | tee ~/.ssh/trezor-github.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIvcbhXyaXXNytCLTDfEMlLuwEhtfo0XmPP1U5RsnOZ4 <ssh://git@github.com|ed25519>
```
##### sign the given file using TREZOR
```
$ trezor-agent -e ed25519 git@github.com -- ssh-keygen -Y sign -f ~/.ssh/trezor-github.pub -n file README.md
Signing file README.md
Write signature to README.md.sig
```
##### set allowed identities for verification (using the above public key)
```
$ cat allowed 
git@github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIvcbhXyaXXNytCLTDfEMlLuwEhtfo0XmPP1U5RsnOZ4 <ssh://git@github.com|ed25519>
```
##### verify the above signature
```
$ ssh-keygen -Y verify -f allowed -I git@github.com -n file -s README.md.sig -vvv < README.md
debug1: sshsig_verify_fd: signature made with hash "sha512"
debug1: sshsig_wrap_verify: verify message length 64
debug1: Valid (unverified) signature from key SHA256:6UBhPb5SOoCUfasGC1/aCBegYov0/P3ajd6eNbYg77A
debug1: parse_principals_key_and_options: allowed:1: matched principal "git@github.com"
debug1: allowed:1: matched key and principal
Good "file" signature for git@github.com with ED25519 key SHA256:6UBhPb5SOoCUfasGC1/aCBegYov0/P3ajd6eNbYg77A
```

## 4. Troubleshooting

If SSH connection fails to work, please open an [issue](https://github.com/romanz/trezor-agent/issues)
with a verbose log attached (by running `trezor-agent -vv`) .

#### `IdentitiesOnly` SSH option

Note that your local SSH configuration may ignore `trezor-agent`, if it has `IdentitiesOnly` option set to `yes`.

     IdentitiesOnly
             Specifies that ssh(1) should only use the authentication identity files configured in
             the ssh_config files, even if ssh-agent(1) or a PKCS11Provider offers more identities.
             The argument to this keyword must be “yes” or “no”.
             This option is intended for situations where ssh-agent offers many different identities.
             The default is “no”.

If you are failing to connect, save your public key using:

	$ trezor-agent -vv foobar@hostname.com > ~/.ssh/hostname.pub

And add the following lines to `~/.ssh/config` (providing the public key explicitly to SSH):

	Host hostname.com
		User foobar
		IdentityFile ~/.ssh/hostname.pub

Then, the following commands should successfully command to the remote host:

	$ trezor-agent -v foobar@hostname.com -s
	$ ssh foobar@hostname.com

or,

	$ trezor-agent -v foobar@hostname.com -c
