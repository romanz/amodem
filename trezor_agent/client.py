"""
Connection to hardware authentication device.

It is used for getting SSH public keys and ECDSA signing of server requests.
"""
import binascii
import io
import logging

from . import factory, formats, util

log = logging.getLogger(__name__)


class Client(object):
    """Client wrapper for SSH authentication device."""

    def __init__(self, loader=factory.load, curve=formats.CURVE_NIST256):
        """Connect to hardware device."""
        client_wrapper = loader()
        self.client = client_wrapper.connection
        self.identity_type = client_wrapper.identity_type
        self.device_name = client_wrapper.device_name
        self.call_exception = client_wrapper.call_exception
        self.curve = curve

    def __enter__(self):
        """Start a session, and test connection."""
        msg = 'Hello World!'
        assert self.client.ping(msg) == msg
        return self

    def __exit__(self, *args):
        """Keep the session open (doesn't forget PIN)."""
        log.info('disconnected from %s', self.device_name)
        self.client.close()

    def get_identity(self, label, index=0):
        """Parse label string into Identity protobuf."""
        identity = util.string_to_identity(label, self.identity_type)
        identity.proto = 'ssh'
        identity.index = index
        return identity

    def get_public_key(self, label):
        """Get SSH public key corresponding to specified by label."""
        identity = self.get_identity(label=label)
        label = util.identity_to_string(identity)  # canonize key label
        log.info('getting "%s" public key (%s) from %s...',
                 label, self.curve, self.device_name)
        addr = util.get_bip32_address(identity)
        node = self.client.get_public_node(n=addr,
                                           ecdsa_curve_name=self.curve)

        pubkey = node.node.public_key
        vk = formats.decompress_pubkey(pubkey=pubkey, curve_name=self.curve)
        return formats.export_public_key(vk=vk, label=label)

    def sign_ssh_challenge(self, label, blob):
        """Sign given blob using a private key, specified by the label."""
        identity = self.get_identity(label=label)
        msg = _parse_ssh_blob(blob)
        log.debug('%s: user %r via %r (%r)',
                  msg['conn'], msg['user'], msg['auth'], msg['key_type'])
        log.debug('nonce: %s', binascii.hexlify(msg['nonce']))
        log.debug('fingerprint: %s', msg['public_key']['fingerprint'])
        log.debug('hidden challenge size: %d bytes', len(blob))

        log.info('please confirm user "%s" login to "%s" using %s...',
                 msg['user'], label, self.device_name)

        try:
            result = self.client.sign_identity(identity=identity,
                                               challenge_hidden=blob,
                                               challenge_visual='',
                                               ecdsa_curve_name=self.curve)
        except self.call_exception as e:
            code, msg = e.args
            log.warning('%s error #%s: %s', self.device_name, code, msg)
            raise IOError(msg)  # close current connection, keep server open

        verifying_key = formats.decompress_pubkey(pubkey=result.public_key,
                                                  curve_name=self.curve)
        key_type, blob = formats.serialize_verifying_key(verifying_key)
        assert blob == msg['public_key']['blob']
        assert key_type == msg['key_type']
        assert len(result.signature) == 65
        assert result.signature[:1] == bytearray([0])

        return result.signature[1:]


def _parse_ssh_blob(data):
    res = {}
    i = io.BytesIO(data)
    res['nonce'] = util.read_frame(i)
    i.read(1)  # SSH2_MSG_USERAUTH_REQUEST == 50 (from ssh2.h, line 108)
    res['user'] = util.read_frame(i)
    res['conn'] = util.read_frame(i)
    res['auth'] = util.read_frame(i)
    i.read(1)  # have_sig == 1 (from sshconnect2.c, line 1056)
    res['key_type'] = util.read_frame(i)
    public_key = util.read_frame(i)
    res['public_key'] = formats.parse_pubkey(public_key)
    assert not i.read()
    return res
