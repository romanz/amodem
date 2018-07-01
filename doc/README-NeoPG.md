# NeoPG experimental support

1. Download build and install NeoPG from [source code](https://github.com/das-labor/neopg#installation).

2. Generate Ed25519-based identity (using a [special wrapper](https://github.com/romanz/trezor-agent/blob/c22109df24c6eb8263aa40183a016be3437b1a0c/contrib/neopg-trezor) to invoke TREZOR-based agent):

```bash
$ export NEOPG_BINARY=$PWD/contrib/neopg-trezor
$ $NEOPG_BINARY --help

$ export GNUPGHOME=/tmp/homedir
$ trezor-gpg init "FooBar" -e ed25519
sec   ed25519 2018-07-01 [SC]
      802AF7E2DCF4491FFBB2F032341E95EF57CD7D5E
uid           [ultimate] FooBar
ssb   cv25519 2018-07-01 [E]
```

3. Sign and verify signatures:
```
$ $NEOPG_BINARY -v --detach-sign FILE
neopg: starting agent '/home/roman/Code/trezor/trezor-agent/contrib/neopg-trezor'
neopg: using pgp trust model
neopg: writing to 'FILE.sig'
neopg: EDDSA/SHA256 signature from: "341E95EF57CD7D5E FooBar"

$ $NEOPG_BINARY --verify FILE.sig FILE
neopg: Signature made Sun Jul  1 11:52:51 2018 IDT
neopg:                using EDDSA key 802AF7E2DCF4491FFBB2F032341E95EF57CD7D5E
neopg: Good signature from "FooBar" [ultimate]
```