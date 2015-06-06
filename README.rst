Using Trezor as a hardware SSH agent
====================================

Sample usage::

	~/Code/trezor/trezor-agent $ ./agent.py -k home
	ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBKJnIA4lKZ1hR2tNUOFmtc8MwAVR4oe0CP5QzSrviSi4joZSTzHcmazK0800w2aj132EEmf1kzl6Vf7h46iCeD8= home
	~/Code/trezor/trezor-agent $ ./agent.py -k home > ~/.ssh/authorized_keys
	~/Code/trezor/trezor-agent $ ./agent.py -k home ssh localhost
	Linux lmde 3.16.0-4-amd64 #1 SMP Debian 3.16.7-ckt9-3~deb8u1 (2015-04-24) x86_64

	The programs included with the Debian GNU/Linux system are free software;
	the exact distribution terms for each program are described in the
	individual files in /usr/share/doc/*/copyright.

	Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
	permitted by applicable law.
	Last login: Sat Jun  6 16:24:12 2015 from localhost
	$

