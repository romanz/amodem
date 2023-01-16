# `age` Agent

Note: the age-related code is still under development, so please try the current implementation
and please let me [know](https://github.com/romanz/trezor-agent/issues/new) if something doesn't
work well for you. If possible:

 * record the session (e.g. using [asciinema](https://asciinema.org))
 * collect the agent log by setting `TREZOR_AGE_PLUGIN_LOG` environment variable

Thanks!

## 1. Configuration

Install [age 1.1.0+](https://github.com/FiloSottile/age/releases/tag/v1.1.0) or [rage 0.9.0+](https://github.com/str4d/rage/releases/tag/v0.9.0).

Generate an identity by running:

```
$ age-plugin-trezor -i "John Doe" | tee identity
# recipient: age1wpl78afms4x36mucnd4j65sanrtj9873up47qq39h68q0aw7n4xqdlw6tk
# SLIP-0017: John Doe
AGE-PLUGIN-TREZOR-1FFHKSM3QG3HK2PEPD5D
```

## 2. Usage

### Encrypt

Use the recipient ID from above (see [age](https://github.com/FiloSottile/age#usage)/[rage](https://github.com/str4d/rage#usage) instructions):
```
$ date | age -r age1wpl78afms4x36mucnd4j65sanrtj9873up47qq39h68q0aw7n4xqdlw6tk > secret.age
```

### Decrypt

Make sure `age-plugin-trezor` is installed and available (it will be invoked by `age` for decryption):

```
$ age -d -i identity < secret.age 
Mon 26 Dec 2022 21:10:26 IST
```

### Manage passwords with `passage`

First install `passage` from https://github.com/FiloSottile/passage and initialize it to use your hardware-based identity:
```
$ mkdir -p ~/.passage/store

$ age-plugin-trezor -i "John Doe" | tee ~/.passage/identities
# recipient: age1wpl78afms4x36mucnd4j65sanrtj9873up47qq39h68q0aw7n4xqdlw6tk
# SLIP-0017: John Doe
AGE-PLUGIN-TREZOR-1FFHKSM3QG3HK2PEPD5D

$ awk '/# recipient:/ {print $3}' ~/.passage/identities | tee -a ~/.passage/store/.age-recipients
age1wpl78afms4x36mucnd4j65sanrtj9873up47qq39h68q0aw7n4xqdlw6tk
```

```
$ passage generate Dev/github 32
$ passage generate Social/hackernews 32
$ passage generate Social/twitter 32
$ passage generate VPS/linode 32
$ passage
Passage
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
$ passage --clip VPS/linode
Copied VPS/linode to clipboard. Will clear in 45 seconds.
```
