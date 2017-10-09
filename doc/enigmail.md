# Tutorial

First, install [Thunderbird](https://www.mozilla.org/en-US/thunderbird/) and
the [Enigmail](https://www.enigmail.net/index.php/en/) add-on.

Make sure to use the correct GNUPGHOME path before starting Thunderbird:
```bash
$ export GNUPGHOME=${HOME}/.gnupg/trezor
$ thunderbird
```
Run the Enigmail's setup wizard and choose your GPG identity:
![01](https://user-images.githubusercontent.com/9900/31327339-47a5f69a-acd7-11e7-997c-7b5a286fe5bc.png)
![02](https://user-images.githubusercontent.com/9900/31327344-51dcd246-acd7-11e7-8cdc-dd305a512dbb.png)
![03](https://user-images.githubusercontent.com/9900/31327346-546862a0-acd7-11e7-8e00-b40994bd6f17.png)

Then, you can compose encrypted (and signed) messages using the regular UI:

NOTES:
 - The email's title is **public** - only the body is encrypted.
 - You will be asked to confirm the signature using the hardware device before sending the email.

![04](https://user-images.githubusercontent.com/9900/31327356-660d098e-acd7-11e7-9e43-762898f5b57e.png)
![05](https://user-images.githubusercontent.com/9900/31327365-76679dda-acd7-11e7-9403-6965f0c6d8fe.png)

After receiving the email, you will be asked to confirm the decryption the hardware device:
![06](https://user-images.githubusercontent.com/9900/31327371-7c1da4cc-acd7-11e7-9a5a-20accf621b49.png)
