# NEVER RUN ON YOUR OWN REAL GPG KEYS!!!!! THEY WILL BE DELETED!!!!!
set -x -e -u
(cd ~/.gnupg && rm -rf openpgp-revocs.d/ private-keys-v1.d/ pubring.kbx* trustdb.gpg /tmp/log *.gpg; killall gpg-agent || true)
gpg2 --full-gen-key --expert
gpg2 --export > romanz.pub
NOW=`date +%s`
trezor-gpg -t $NOW "romanz" -o subkey.pub
gpg2 -K
gpg2 -vv --import <(cat romanz.pub subkey.pub)
gpg2 -K

trezor-gpg -t $NOW "romanz" EXAMPLE
gpg2 --verify EXAMPLE.sig
