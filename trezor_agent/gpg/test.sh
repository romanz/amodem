set -x
(cd ~/.gnupg && rm -r openpgp-revocs.d/ private-keys-v1.d/ pubring.kbx* trustdb.gpg /tmp/log *.gpg; killall gpg-agent)
gpg2 --full-gen-key --expert
gpg2 --export > romanz.pub
NOW=`date +%s`; trezor-gpg -t $NOW "romanz" -o subkey.pub
gpg2 -vv --import <(cat romanz.pub subkey.pub)
gpg2 -k
