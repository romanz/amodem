import io
import struct
import hashlib
import ecdsa
import base64

import logging
log = logging.getLogger(__name__)

def send(conn, data, fmt=None):
    if fmt:
        data = struct.pack(fmt, *data)
    conn.sendall(data)

def recv(conn, size):
    try:
        fmt = size
        size = struct.calcsize(fmt)
    except TypeError:
        fmt = None
    try:
        _read = conn.recv
    except AttributeError:
        _read = conn.read

    res = io.BytesIO()
    while size > 0:
        buf = _read(size)
        if not buf:
            raise EOFError
        size = size - len(buf)
        res.write(buf)
    res = res.getvalue()
    if fmt:
        return struct.unpack(fmt, res)
    else:
        return res


def read_frame(conn):
    size, = recv(conn, '>L')
    return recv(conn, size)

def bytes2num(s):
    res = 0
    for i, c in enumerate(reversed(bytearray(s))):
        res += c << (i * 8)
    return res


def parse_pubkey(blob):
    s = io.BytesIO(blob)
    key_type = read_frame(s)
    log.debug('key type: %s', key_type)
    curve = read_frame(s)
    log.debug('curve name: %s', curve)
    point = read_frame(s)
    _type, point = point[:1], point[1:]
    assert _type == DER_OCTET_STRING
    size = len(point) // 2
    assert len(point) == 2 * size
    coords = map(bytes2num, [point[:size], point[size:]])
    log.debug('coordinates: %s', coords)
    fp = fingerprint(blob)
    result = {
        'point': tuple(coords), 'curve': curve,
        'fingerprint': fp,
        'type': key_type,
        'blob': blob, 'size': size
    }
    return result

def list_keys(c):
    send(c, [0x1, 0xB], '>LB')
    buf = io.BytesIO(read_frame(c))
    assert recv(buf, '>B') == (0xC,)
    num, = recv(buf, '>L')
    for i in range(num):
        k = parse_pubkey(read_frame(buf))
        k['comment'] = read_frame(buf)
        yield k

def frame(*msgs):
    res = io.BytesIO()
    for msg in msgs:
        res.write(msg)
    msg = res.getvalue()
    return pack('L', len(msg)) + msg

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

def pack(fmt, *args):
    return struct.pack('>' + fmt, *args)

def legacy_pubs(buf, keys, signer):
    code = pack('B', SSH_AGENT_RSA_IDENTITIES_ANSWER)
    num = pack('L', 0)  # no SSH v1 keys
    return frame(code, num)

def list_pubs(buf, keys, signer):
    code = pack('B', SSH2_AGENT_IDENTITIES_ANSWER)
    num = pack('L', len(keys))
    log.debug('available keys: %s', [k['name'] for k in keys])
    for i, k in enumerate(keys):
        log.debug('%2d) %s', i+1, k['fingerprint'])
    pubs = [frame(k['blob']) + frame(k['name']) for k in keys]
    return frame(code, num, *pubs)

def fingerprint(blob):
    digest = hashlib.md5(blob).digest()
    return ':'.join('{:02x}'.format(c) for c in bytearray(digest))

def num2bytes(value, size):
    res = []
    for i in range(size):
        res.append(value & 0xFF)
        value = value >> 8
    assert value == 0
    return bytearray(list(reversed(res)))

def sign_message(buf, keys, signer):
    key = parse_pubkey(read_frame(buf))
    log.debug('looking for %s', key['fingerprint'])
    blob = read_frame(buf)

    for k in keys:
        if (k['fingerprint']) == (key['fingerprint']):
            log.debug('using key %r (%s)', k['name'], k['fingerprint'])
            key = k
            break
    else:
        raise ValueError('key not found')

    log.debug('signing %d-byte blob', len(blob))
    r, s = signer(label=k['name'], blob=blob)
    signature = (r, s)

    log.debug('signature: %s', signature)

    curve = ecdsa.curves.NIST256p
    point = ecdsa.ellipticcurve.Point(curve.curve, *key['point'])
    vk = ecdsa.VerifyingKey.from_public_point(point, curve, hashlib.sha256)
    success = vk.verify(signature=signature, data=blob,
                        sigdecode=lambda sig, _: sig)
    log.info('signature status: %s', 'OK' if success else 'ERROR')
    if not success:
        raise ValueError('invalid signature')

    sig_bytes = io.BytesIO()
    for x in signature:
        sig_bytes.write(frame(b'\x00' + num2bytes(x, key['size'])))
    sig_bytes = sig_bytes.getvalue()
    log.debug('signature size: %d bytes', len(sig_bytes))

    data = frame(frame(key['type']), frame(sig_bytes))
    code = pack('B', SSH2_AGENT_SIGN_RESPONSE)
    return frame(code, data)

handlers = {
    SSH_AGENTC_REQUEST_RSA_IDENTITIES: legacy_pubs,
    SSH2_AGENTC_REQUEST_IDENTITIES: list_pubs,
    SSH2_AGENTC_SIGN_REQUEST: sign_message,
}

def handle_connection(conn, keys, signer):
    try:
        log.debug('welcome agent')
        while True:
            msg = read_frame(conn)
            buf = io.BytesIO(msg)
            code, = recv(buf, '>B')
            log.debug('request: %d bytes', len(msg))
            handler = handlers[code]
            log.debug('calling %s()', handler.__name__)
            reply = handler(buf=buf, keys=keys, signer=signer)
            log.debug('reply: %d bytes', len(reply))
            send(conn, reply)
    except EOFError:
        log.debug('goodbye agent')
    except:
        log.exception('error')
        raise

DER_OCTET_STRING = b'\x04'

def load_public_key(filename):
    with open(filename) as f:
        return parse_public_key(f.read())

def parse_public_key(data):
    file_type, base64blob, name = data.split()
    blob = base64.b64decode(base64blob)
    result = parse_pubkey(blob)
    result['name'] = name.encode('ascii')
    assert result['type'] == file_type.encode('ascii')
    log.debug('loaded %s %s', file_type, result['fingerprint'])
    return result
