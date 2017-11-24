# Design

Most cryptographic tools (such as gpg, ssh and openssl) allow the offloading of some key cryptographic steps to *engines* or *agents*. This is to allow sensitive operations, such as asking for a password or doing the actual encryption step, to be kept separate from the larger body of code. This makes it easier to secure those steps, move them onto hardware or easier to audit.

SSH and GPG do this by means of a simple interprocess communication protocol (usually a unix domain socket) and an agent (`ssh-agent`) or GPG key daemon (`gpg-agent`).  The `trezor-agent` mimics these two protocols.

These two agents make the connection between the front end (e.g. a `gpg --sign` command, or an `ssh user@fqdn`). And then they wait for a request from the 'front end', and then do the actual asking for a password and subsequent using the private key to sign or decrypt something.

The various hardware wallets (Trezor, KeepKey and Ledger) each have the ability (as of Firmware 1.3.4) to use the NIST P-256 elliptic curve to sign, encrypt or decrypt. This curve can be used with S/MIME, GPG and SSH.

So when you `ssh` to a machine - rather than consult the normal ssh-agent (which in turn will use your private SSH key in files such as `~/.ssh/id_rsa`) -- the trezor-agent will aks your hardware wallet to use its private key to sign the challenge.

## Key Naming

`trezor-agent` goes to great length to avoid using the valuable parent key. 

The rationale behind this is that `trezor-agent` is to some extent condemned to *blindly* signing any NONCE given to it (e.g. as part of a challenge respone, or as the hash/hmac of someting to sign). 

And doing so with the master private key is risky - as rogue (ssh) server could possibly provide a doctored NONCE that happens to be tied to a transaction or something else. 

It therefore uses only derived child keys pairs instead (according to the [BIP-0032: Hierarchical Deterministic Wallets][1] system) - and ones on different leafs. So the parent key is only used within the device for creating the child keys - and not exposed in any way to `trezor-agent`.

### SSH

It is common for SSH users to use one (or a few) private keys with SSH on all servers they log into. The `trezor-agent` is slightly more cautious and derives a child key that is *unique* to the server and username you are logging into from your master private key on the device.

So taking a commmand such as:

	$ trezor-agent -c user@fqdn.com 

The `trezor-agent` will take the `user`@`fqdn.com`; canonicalise it (e.g. to add the ssh default port number if none was specified) and then apply some simple hashing (See [SLIP-0013 : Authentication using deterministic hierarchy][2]). The resulting 128bit hash is then used to construct a lead 'HD node' that contains an extened public private *child* key.

This way they keypair is specific to the server/hostname/port and protocol combination used. And it is this private key that is used to sign the nonce passed by the SSH server (as opposed to the master key).

The `trezor-agent` then instructs SSH to connect to the server. It will then engage in the normal challenge response process, ask the hardware wallet to blindly sign any nonce flashed by the server with the derived child private key and return this to the server. It then hands over to normal SSH for the rest of the logged in session.

### GPG

GPG uses much the same approach as SSH, expect in this it relies on [SLIP-0017 : ECDH using deterministic hierarchy][3] for the mapping to an ECDH key and it maps these to the normal GPG child key infrastructure.

Note: Keepkey does not support en-/de-cryption at this time.

### Index

The canonicalisation process ([SLIP-0013][2] and [SLIP-0017][3]) of an email address or ssh address allows for the mixing in of an extra 'index' - a unsigned 32 bit number. This allows one to have multiple, different keys, for the same address. 

This feature is currently not used -- it is set to '0'. This may change in the future.

[1]: https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki 
[2]: https://github.com/satoshilabs/slips/blob/master/slip-0013.md
[3]: https://github.com/satoshilabs/slips/blob/master/slip-0017.md
