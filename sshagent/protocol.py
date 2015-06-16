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


def legacy_pubs(buf, keys, signer):
    code = util.pack('B', SSH_AGENT_RSA_IDENTITIES_ANSWER)
    num = util.pack('L', 0)  # no SSH v1 keys
    return util.frame(code, num)


def list_pubs(buf, keys, signer):
    code = util.pack('B', SSH2_AGENT_IDENTITIES_ANSWER)
    num = util.pack('L', len(keys))
    log.debug('available keys: %s', [k['name'] for k in keys])
    for i, k in enumerate(keys):
        log.debug('%2d) %s', i+1, k['fingerprint'])
    pubs = [util.frame(k['blob']) + util.frame(k['name']) for k in keys]
    return util.frame(code, num, *pubs)


def sign_message(buf, keys, signer):
    key = formats.parse_pubkey(util.read_frame(buf))
    log.debug('looking for %s', key['fingerprint'])
    blob = util.read_frame(buf)

    for k in keys:
        if (k['fingerprint']) == (key['fingerprint']):
            log.debug('using key %r (%s)', k['name'], k['fingerprint'])
            key = k
            break
    else:
        raise ValueError('key not found')

    log.debug('signing %d-byte blob', len(blob))
    r, s = signer(label=key['name'], blob=blob)
    signature = (r, s)
    log.debug('signature: %s', signature)

    success = key['verifying_key'].verify(signature=signature, data=blob,
                                          sigdecode=lambda sig, _: sig)
    log.info('signature status: %s', 'OK' if success else 'ERROR')
    if not success:
        raise ValueError('invalid signature')

    sig_bytes = io.BytesIO()
    for x in signature:
        sig_bytes.write(util.frame(b'\x00' + util.num2bytes(x, key['size'])))
    sig_bytes = sig_bytes.getvalue()
    log.debug('signature size: %d bytes', len(sig_bytes))

    data = util.frame(util.frame(key['type']), util.frame(sig_bytes))
    code = util.pack('B', SSH2_AGENT_SIGN_RESPONSE)
    return util.frame(code, data)


handlers = {
    SSH_AGENTC_REQUEST_RSA_IDENTITIES: legacy_pubs,
    SSH2_AGENTC_REQUEST_IDENTITIES: list_pubs,
    SSH2_AGENTC_SIGN_REQUEST: sign_message,
}


def handle_message(msg, keys, signer):
    log.debug('request: %d bytes', len(msg))
    buf = io.BytesIO(msg)
    code, = util.recv(buf, '>B')
    handler = handlers[code]
    log.debug('calling %s()', handler.__name__)
    reply = handler(buf=buf, keys=keys, signer=signer)
    log.debug('reply: %d bytes', len(reply))
    return reply
