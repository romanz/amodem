# Custom PIN entry

By default a standard GPG PIN entry program is used when entering your Trezor PIN, but it's difficult to use if you don't have a numeric keypad or want to use your mouse.

You can specify a custom PIN entry program (and separately, a passphrase entry program) such as [trezor-gpg-pinentry-tk](https://github.com/rendaw/trezor-gpg-pinentry-tk) to match your workflow.

The below examples use `trezor-gpg-pinentry-tk` but any GPG compatible PIN entry can be used.

##### 1. Install the PIN entry

Run

```
pip install trezor-gpg-pinentry-tk
```

##### 2. SSH

Add the flag `--pin-entry-binary trezor-gpg-pinentry-tk` to all calls to `trezor-agent`.

To automatically use this flag, add the line `pinentry=trezor-gpg-pinentry-tk` to `~/.ssh/agent.config`.  **Note** this is currently broken due to [this dependency issue](https://github.com/bw2/ConfigArgParse/issues/114).

If you run the SSH agent with Systemd you'll need to add `--pin-entry-binary` to the `ExecStart` command.  You may also need to add this line:

```
Environment="DISPLAY=:0"
```

to the `[Service]` section to tell the PIN entry program how to connect to the X11 server.

##### 3. GPG

If you haven't completed initialization yet, run:

```
$ (trezor|keepkey|ledger)-gpg init --pin-entry-binary trezor-gpg-pinentry-tk "Roman Zeyde <roman.zeyde@gmail.com>"
```

to configure the PIN entry at the same time.

Otherwise, open `$GNUPGHOME/trezor/run-agent.sh` and change the `--pin-entry-binary` option to `trezor-gpg-pinentry-tk` and run:

```
killall trezor-gpg-agent
```

##### 4. Troubleshooting

Any problems running the PIN entry program with GPG should appear in `$HOME/.gnupg/trezor/gpg-agent.log`.

You can get similar logs for SSH by specifying `--log-file` in the SSH command line.