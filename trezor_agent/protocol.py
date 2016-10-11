"""
SSH-agent protocol implementation library.

See https://github.com/openssh/openssh-portable/blob/master/PROTOCOL.agent and
http://ptspts.blogspot.co.il/2010/06/how-to-use-ssh-agent-programmatically.html
for more details.
The server's source code can be found here:
https://github.com/openssh/openssh-portable/blob/master/authfd.c
"""
import binascii
import io
import logging

from . import formats, util

log = logging.getLogger(__name__)


# Taken from https://github.com/openssh/openssh-portable/blob/master/authfd.h
COMMANDS = dict(
    SSH_AGENTC_REQUEST_RSA_IDENTITIES=1,
    SSH_AGENT_RSA_IDENTITIES_ANSWER=2,
    SSH_AGENTC_RSA_CHALLENGE=3,
    SSH_AGENT_RSA_RESPONSE=4,
    SSH_AGENT_FAILURE=5,
    SSH_AGENT_SUCCESS=6,
    SSH_AGENTC_ADD_RSA_IDENTITY=7,
    SSH_AGENTC_REMOVE_RSA_IDENTITY=8,
    SSH_AGENTC_REMOVE_ALL_RSA_IDENTITIES=9,
    SSH2_AGENTC_REQUEST_IDENTITIES=11,
    SSH2_AGENT_IDENTITIES_ANSWER=12,
    SSH2_AGENTC_SIGN_REQUEST=13,
    SSH2_AGENT_SIGN_RESPONSE=14,
    SSH2_AGENTC_ADD_IDENTITY=17,
    SSH2_AGENTC_REMOVE_IDENTITY=18,
    SSH2_AGENTC_REMOVE_ALL_IDENTITIES=19,
    SSH_AGENTC_ADD_SMARTCARD_KEY=20,
    SSH_AGENTC_REMOVE_SMARTCARD_KEY=21,
    SSH_AGENTC_LOCK=22,
    SSH_AGENTC_UNLOCK=23,
    SSH_AGENTC_ADD_RSA_ID_CONSTRAINED=24,
    SSH2_AGENTC_ADD_ID_CONSTRAINED=25,
    SSH_AGENTC_ADD_SMARTCARD_KEY_CONSTRAINED=26,
)


def msg_code(name):
    """Convert string name into a integer message code."""
    return COMMANDS[name]


def msg_name(code):
    """Convert integer message code into a string name."""
    ids = {v: k for k, v in COMMANDS.items()}
    return ids[code]


def failure():
    """Return error code to SSH binary."""
    error_msg = util.pack('B', msg_code('SSH_AGENT_FAILURE'))
    return util.frame(error_msg)


def _legacy_pubs(buf):
    """SSH v1 public keys are not supported."""
    assert not buf.read()
    code = util.pack('B', msg_code('SSH_AGENT_RSA_IDENTITIES_ANSWER'))
    num = util.pack('L', 0)  # no SSH v1 keys
    return util.frame(code, num)


class Handler(object):
    """ssh-agent protocol handler."""

    def __init__(self, keys, signer, debug=False):
        """
        Create a protocol handler with specified public keys.

        Use specified signer function to sign SSH authentication requests.
        """
        self.public_keys = keys
        self.signer = signer
        self.debug = debug

        self.methods = {
            msg_code('SSH_AGENTC_REQUEST_RSA_IDENTITIES'): _legacy_pubs,
            msg_code('SSH2_AGENTC_REQUEST_IDENTITIES'): self.list_pubs,
            msg_code('SSH2_AGENTC_SIGN_REQUEST'): self.sign_message,
        }

    def handle(self, msg):
        """Handle SSH message from the SSH client and return the response."""
        debug_msg = ': {!r}'.format(msg) if self.debug else ''
        log.debug('request: %d bytes%s', len(msg), debug_msg)
        buf = io.BytesIO(msg)
        code, = util.recv(buf, '>B')
        if code not in self.methods:
            log.warning('Unsupported command: %s (%d)', msg_name(code), code)
            return failure()

        method = self.methods[code]
        log.debug('calling %s()', method.__name__)
        reply = method(buf=buf)
        debug_reply = ': {!r}'.format(reply) if self.debug else ''
        log.debug('reply: %d bytes%s', len(reply), debug_reply)
        return reply

    def list_pubs(self, buf):
        """SSH v2 public keys are serialized and returned."""
        assert not buf.read()
        keys = self.public_keys
        code = util.pack('B', msg_code('SSH2_AGENT_IDENTITIES_ANSWER'))
        num = util.pack('L', len(keys))
        log.debug('available keys: %s', [k['name'] for k in keys])
        for i, k in enumerate(keys):
            log.debug('%2d) %s', i+1, k['fingerprint'])
        pubs = [util.frame(k['blob']) + util.frame(k['name']) for k in keys]
        return util.frame(code, num, *pubs)

    def sign_message(self, buf):
        """
        SSH v2 public key authentication is performed.

        If the required key is not supported, raise KeyError
        If the signature is invalid, raise ValueError
        """
        key = formats.parse_pubkey(util.read_frame(buf))
        log.debug('looking for %s', key['fingerprint'])
        blob = util.read_frame(buf)
        assert util.read_frame(buf) == b''
        assert not buf.read()

        for k in self.public_keys:
            if (k['fingerprint']) == (key['fingerprint']):
                log.debug('using key %r (%s)', k['name'], k['fingerprint'])
                key = k
                break
        else:
            raise KeyError('key not found')

        log.debug('signing %d-byte blob', len(blob))
        label = key['name'].decode('ascii')  # label should be a string
        try:
            signature = self.signer(label=label, blob=blob)
        except IOError:
            return failure()
        log.debug('signature: %s', binascii.hexlify(signature))

        try:
            sig_bytes = key['verifier'](sig=signature, msg=blob)
            log.info('signature status: OK')
        except formats.ecdsa.BadSignatureError:
            log.exception('signature status: ERROR')
            raise ValueError('invalid ECDSA signature')

        log.debug('signature size: %d bytes', len(sig_bytes))

        data = util.frame(util.frame(key['type']), util.frame(sig_bytes))
        code = util.pack('B', msg_code('SSH2_AGENT_SIGN_RESPONSE'))
        return util.frame(code, data)
