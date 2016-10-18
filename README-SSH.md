# Screencast demo usage

## Simple usage (single SSH session)
[![Demo](https://asciinema.org/a/22959.png)](https://asciinema.org/a/22959)

## Advanced usage (multiple SSH sessions from a sub-shell)
[![Subshell](https://asciinema.org/a/33240.png)](https://asciinema.org/a/33240)

## Using for GitHub SSH authentication (via `trezor-git` utility)
[![GitHub](https://asciinema.org/a/38337.png)](https://asciinema.org/a/38337)

# Public key generation

Run:

	/tmp $ trezor-agent user@ssh.hostname.com -v > hostname.pub
	2015-09-02 15:03:18,929 INFO         getting "ssh://user@ssh.hostname.com" public key from Trezor...
	2015-09-02 15:03:23,342 INFO         disconnected from Trezor
	/tmp $ cat hostname.pub
	ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGSevcDwmT+QaZPUEWUUjTeZRBICChxMKuJ7dRpBSF8+qt+8S1GBK5Zj8Xicc8SHG/SE/EXKUL2UU3kcUzE7ADQ= ssh://user@ssh.hostname.com

Append `hostname.pub` contents to `/home/user/.ssh/authorized_keys`
configuration file at `ssh.hostname.com`, so the remote server
would allow you to login using the corresponding private key signature.

# Usage

Run:

	/tmp $ trezor-agent user@ssh.hostname.com -v -c
	2015-09-02 15:09:39,782 INFO         getting "ssh://user@ssh.hostname.com" public key from Trezor...
	2015-09-02 15:09:44,430 INFO         please confirm user "roman" login to "ssh://user@ssh.hostname.com" using Trezor...
	2015-09-02 15:09:46,152 INFO         signature status: OK
	Linux lmde 3.16.0-4-amd64 #1 SMP Debian 3.16.7-ckt11-1+deb8u3 (2015-08-04) x86_64

	The programs included with the Debian GNU/Linux system are free software;
	the exact distribution terms for each program are described in the
	individual files in /usr/share/doc/*/copyright.

	Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
	permitted by applicable law.
	Last login: Tue Sep  1 15:57:05 2015 from localhost
	~ $

Make sure to confirm SSH signature on the Trezor device when requested.

## Accessing remote Git repositories

Use your SSH public key to access your remote repository (e.g. [GitHub](https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/)):

	$ trezor-agent -v -e ed25519 git@github.com | xclip

Use the following Bash alias for convinient Git operations:

	$ alias git_hub='trezor-agent -v -e ed25519 git@github.com -- git'

Replace `git` with `git_hub` for remote operations:

	$ git_hub push origin master
