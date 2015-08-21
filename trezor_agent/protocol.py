import io

from . import util
from . import formats

import logging
log = logging.getLogger(__name__)

SSH_AGENTC_REQUEST_RSA_IDENTITIES = 1
SSH_AGENT_RSA_IDENTITIES_ANSWER = 2

SSH_AGENTC_REMOVE_ALL_RSA_IDENTITIES = 9

SSH2_AGENTC_REQUEST_IDENTITIES = 11
SSH2_AGENT_IDENTITIES_ANSWER = 12
SSH2_AGENTC_SIGN_REQUEST = 13
SSH2_AGENT_SIGN_RESPONSE = 14
SSH2_AGENTC_ADD_IDENTITY = 17
SSH2_AGENTC_REMOVE_IDENTITY = 18
SSH2_AGENTC_REMOVE_ALL_IDENTITIES = 19


class Error(Exception):
    pass


class BadSignature(Error):
    pass


class MissingKey(Error):
    pass


class Handler(object):

    def __init__(self, keys, signer):
        self.public_keys = keys
        self.signer = signer

        self.methods = {
            SSH_AGENTC_REQUEST_RSA_IDENTITIES: Handler.legacy_pubs,
            SSH2_AGENTC_REQUEST_IDENTITIES: self.list_pubs,
            SSH2_AGENTC_SIGN_REQUEST: self.sign_message,
        }

    def handle(self, msg):
        log.debug('request: %d bytes', len(msg))
        buf = io.BytesIO(msg)
        code, = util.recv(buf, '>B')
        method = self.methods[code]
        log.debug('calling %s()', method.__name__)
        reply = method(buf=buf)
        log.debug('reply: %d bytes', len(reply))
        return reply

    @staticmethod
    def legacy_pubs(buf):
        ''' SSH v1 public keys are not supported '''
        assert not buf.read()
        code = util.pack('B', SSH_AGENT_RSA_IDENTITIES_ANSWER)
        num = util.pack('L', 0)  # no SSH v1 keys
        return util.frame(code, num)

    def list_pubs(self, buf):
        ''' SSH v2 public keys are serialized and returned. '''
        assert not buf.read()
        keys = self.public_keys
        code = util.pack('B', SSH2_AGENT_IDENTITIES_ANSWER)
        num = util.pack('L', len(keys))
        log.debug('available keys: %s', [k['name'] for k in keys])
        for i, k in enumerate(keys):
            log.debug('%2d) %s', i+1, k['fingerprint'])
        pubs = [util.frame(k['blob']) + util.frame(k['name']) for k in keys]
        return util.frame(code, num, *pubs)

    def sign_message(self, buf):
        ''' SSH v2 public key authentication is performed. '''
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
            raise MissingKey('key not found')

        log.debug('signing %d-byte blob', len(blob))
        r, s = self.signer(label=key['name'], blob=blob)
        signature = (r, s)
        log.debug('signature: %s', signature)

        try:
            key['verifying_key'].verify(signature=signature, data=blob,
                                        sigdecode=lambda sig, _: sig)
            log.info('signature status: OK')
        except formats.ecdsa.BadSignatureError:
            log.exception('signature status: ERROR')
            raise BadSignature('invalid ECDSA signature')

        sig_bytes = io.BytesIO()
        for x in signature:
            x_frame = util.frame(b'\x00' + util.num2bytes(x, key['size']))
            sig_bytes.write(x_frame)
        sig_bytes = sig_bytes.getvalue()
        log.debug('signature size: %d bytes', len(sig_bytes))

        data = util.frame(util.frame(key['type']), util.frame(sig_bytes))
        code = util.pack('B', SSH2_AGENT_SIGN_RESPONSE)
        return util.frame(code, data)
