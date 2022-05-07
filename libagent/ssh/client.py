"""
Connection to hardware authentication device.

It is used for getting SSH public keys and ECDSA signing of server requests.
"""
import io
import logging

from . import formats, util

log = logging.getLogger(__name__)


class Client:
    """Client wrapper for SSH authentication device."""

    def __init__(self, device):
        """Connect to hardware device."""
        self.device = device

    def export_public_keys(self, identities):
        """Export SSH public keys from the device."""
        pubkeys = []
        with self.device:
            for i in identities:
                vk = self.device.pubkey(identity=i)
                label = i.to_string()
                pubkey = formats.export_public_key(vk=vk, label=label)
                pubkeys.append(pubkey)
        return pubkeys

    def sign_ssh_challenge(self, blob, identity):
        """Sign given blob using a private key on the device."""
        log.debug('blob: %r', blob)
        msg = parse_ssh_blob(blob)
        if msg['sshsig']:
            log.info('please confirm "%s" signature for "%s" using %s...',
                     msg['namespace'], identity.to_string(), self.device)
        else:
            log.debug('%s: user %r via %r (%r)',
                      msg['conn'], msg['user'], msg['auth'], msg['key_type'])
            log.debug('nonce: %r', msg['nonce'])
            fp = msg['public_key']['fingerprint']
            log.debug('fingerprint: %s', fp)
            log.debug('hidden challenge size: %d bytes', len(blob))

            log.info('please confirm user "%s" login to "%s" using %s...',
                     msg['user'].decode('ascii'), identity.to_string(),
                     self.device)

        with self.device:
            return self.device.sign(blob=blob, identity=identity)


def parse_ssh_blob(data):
    """Parse binary data into a dict."""
    res = {}
    if data.startswith(b'SSHSIG'):
        i = io.BytesIO(data[6:])
        # https://github.com/openssh/openssh-portable/blob/master/PROTOCOL.sshsig
        res['sshsig'] = True
        res['namespace'] = util.read_frame(i)
        res['reserved'] = util.read_frame(i)
        res['hashalg'] = util.read_frame(i)
        res['message'] = util.read_frame(i)
    else:
        i = io.BytesIO(data)
        res['sshsig'] = False
        res['nonce'] = util.read_frame(i)
        i.read(1)  # SSH2_MSG_USERAUTH_REQUEST == 50 (from ssh2.h, line 108)
        res['user'] = util.read_frame(i)
        res['conn'] = util.read_frame(i)
        res['auth'] = util.read_frame(i)
        i.read(1)  # have_sig == 1 (from sshconnect2.c, line 1056)
        res['key_type'] = util.read_frame(i)
        public_key = util.read_frame(i)
        res['public_key'] = formats.parse_pubkey(public_key)

    unparsed = i.read()
    if unparsed:
        log.warning('unparsed blob: %r', unparsed)
    return res
