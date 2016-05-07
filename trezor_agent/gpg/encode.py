"""Create GPG ECDSA signatures and public keys using TREZOR device."""
import base64
import hashlib
import logging
import struct
import time

from . import agent, decode, proto
from .. import client, factory, formats, util

log = logging.getLogger(__name__)


class HardwareSigner(object):
    """Sign messages and get public keys from a hardware device."""

    def __init__(self, user_id, curve_name):
        """Connect to the device and retrieve required public key."""
        self.client_wrapper = factory.load()
        self.identity = self.client_wrapper.identity_type()
        self.identity.proto = 'gpg'
        self.identity.host = user_id
        self.curve_name = curve_name

    def pubkey(self):
        """Return public key as VerifyingKey object."""
        addr = client.get_address(self.identity)
        public_node = self.client_wrapper.connection.get_public_node(
            n=addr, ecdsa_curve_name=self.curve_name)

        return formats.decompress_pubkey(
            pubkey=public_node.node.public_key,
            curve_name=self.curve_name)

    def sign(self, digest):
        """Sign the digest and return a serialized signature."""
        result = self.client_wrapper.connection.sign_identity(
            identity=self.identity,
            challenge_hidden=digest,
            challenge_visual=util.hexlify(digest),
            ecdsa_curve_name=self.curve_name)
        assert result.signature[:1] == b'\x00'
        sig = result.signature[1:]
        return (proto.mpi(util.bytes2num(sig[:32])) +
                proto.mpi(util.bytes2num(sig[32:])))

    def close(self):
        """Close the connection to the device."""
        self.client_wrapper.connection.clear_session()
        self.client_wrapper.connection.close()


class AgentSigner(object):
    """Sign messages and get public keys using gpg-agent tool."""

    def __init__(self, user_id):
        """Connect to the agent and retrieve required public key."""
        self.sock = agent.connect()
        self.keygrip = agent.get_keygrip(user_id)
        self.public_key = decode.load_from_gpg(user_id)

    def pubkey(self):
        """Return public key as VerifyingKey object."""
        return self.public_key['verifying_key']

    def sign(self, digest):
        """Sign the digest and return an ECDSA signature."""
        params = agent.sign(sock=self.sock,
                            keygrip=self.keygrip, digest=digest)
        return b''.join(proto.mpi(p) for p in params)

    def close(self):
        """Close the connection to gpg-agent."""
        self.sock.close()


class PublicKey(object):
    """GPG representation for public key packets."""

    def __init__(self, curve_name, created, verifying_key):
        """Contruct using a ECDSA VerifyingKey object."""
        self.curve_info = proto.SUPPORTED_CURVES[curve_name]
        self.created = int(created)  # time since Epoch
        self.verifying_key = verifying_key
        self.algo_id = self.curve_info['algo_id']

    def data(self):
        """Data for packet creation."""
        header = struct.pack('>BLB',
                             4,             # version
                             self.created,  # creation
                             self.algo_id)  # public key algorithm ID
        oid = util.prefix_len('>B', self.curve_info['oid'])
        blob = self.curve_info['serialize'](self.verifying_key)
        return header + oid + blob

    def data_to_hash(self):
        """Data for digest computation."""
        return b'\x99' + util.prefix_len('>H', self.data())

    def _fingerprint(self):
        return hashlib.sha1(self.data_to_hash()).digest()

    def key_id(self):
        """Short (8 byte) GPG key ID."""
        return self._fingerprint()[-8:]

    def __repr__(self):
        """Short (8 hexadecimal digits) GPG key ID."""
        return '<{}>'.format(util.hexlify(self.key_id()))

    __str__ = __repr__


class Signer(object):
    """Performs GPG signing operations."""

    def __init__(self, user_id, created, curve_name):
        """Construct and loads a public key from the device."""
        self.user_id = user_id
        assert curve_name in formats.SUPPORTED_CURVES

        self.conn = HardwareSigner(user_id, curve_name=curve_name)
        self.pubkey = PublicKey(
            curve_name=curve_name, created=created,
            verifying_key=self.conn.pubkey())

        log.info('%s GPG public key %s created at %s for "%s"',
                 curve_name, self.pubkey,
                 util.time_format(self.pubkey.created), user_id)

    @classmethod
    def from_public_key(cls, pubkey, user_id):
        """
        Create from an existing GPG public key.

        `pubkey` should be loaded via `decode.load_from_gpg(user_id)`
        from the local GPG keyring.
        """
        s = Signer(user_id=user_id,
                   created=pubkey['created'],
                   curve_name=proto.find_curve_by_algo_id(pubkey['algo']))
        assert s.pubkey.key_id() == pubkey['key_id']
        return s

    def close(self):
        """Close connection and turn off the screen of the device."""
        self.conn.close()

    def export(self):
        """Export GPG public key, ready for "gpg2 --import"."""
        pubkey_packet = proto.packet(tag=6, blob=self.pubkey.data())
        user_id_packet = proto.packet(tag=13, blob=self.user_id)

        data_to_sign = (self.pubkey.data_to_hash() +
                        user_id_packet[:1] +
                        util.prefix_len('>L', self.user_id))
        log.info('signing public key "%s"', self.user_id)
        hashed_subpackets = [
            proto.subpacket_time(self.pubkey.created),  # signature time
            proto.subpacket_byte(0x1B, 1 | 2),  # key flags (certify & sign)
            proto.subpacket_byte(0x15, 8),  # preferred hash (SHA256)
            proto.subpacket_byte(0x16, 0),  # preferred compression (none)
            proto.subpacket_byte(0x17, 0x80)]  # key server prefs (no-modify)
        unhashed_subpackets = [
            proto.subpacket(16, self.pubkey.key_id()),  # issuer key id
            proto.CUSTOM_SUBPACKET]

        signature = _make_signature(
            signer_func=self.conn.sign,
            public_algo=self.pubkey.algo_id,
            data_to_sign=data_to_sign,
            sig_type=0x13,  # user id & public key
            hashed_subpackets=hashed_subpackets,
            unhashed_subpackets=unhashed_subpackets)

        sign_packet = proto.packet(tag=2, blob=signature)
        return pubkey_packet + user_id_packet + sign_packet

    def subkey(self):
        """Export a subkey to `self.user_id` GPG primary key."""
        subkey_packet = proto.packet(tag=14, blob=self.pubkey.data())
        primary = decode.load_from_gpg(self.user_id)
        log.info('adding subkey to primary GPG key "%s" (%s)',
                 self.user_id, util.hexlify(primary['key_id']))
        data_to_sign = primary['_to_hash'] + self.pubkey.data_to_hash()

        # Primary Key Binding Signature
        hashed_subpackets = [
            proto.subpacket_time(self.pubkey.created)]  # signature time
        unhashed_subpackets = [
            proto.subpacket(16, self.pubkey.key_id())]  # issuer key id
        log.info('confirm signing subkey with hardware device')
        embedded_sig = _make_signature(signer_func=self.conn.sign,
                                       data_to_sign=data_to_sign,
                                       public_algo=self.pubkey.algo_id,
                                       sig_type=0x19,
                                       hashed_subpackets=hashed_subpackets,
                                       unhashed_subpackets=unhashed_subpackets)

        # Subkey Binding Signature
        hashed_subpackets = [
            proto.subpacket_time(self.pubkey.created),  # signature time
            proto.subpacket_byte(0x1B, 2)]  # key flags (certify & sign)
        unhashed_subpackets = [
            proto.subpacket(16, primary['key_id']),  # issuer key id
            proto.subpacket(32, embedded_sig),
            proto.CUSTOM_SUBPACKET]
        log.info('confirm signing subkey with gpg-agent')
        gpg_agent = AgentSigner(self.user_id)
        signature = _make_signature(signer_func=gpg_agent.sign,
                                    data_to_sign=data_to_sign,
                                    public_algo=primary['algo'],
                                    sig_type=0x18,
                                    hashed_subpackets=hashed_subpackets,
                                    unhashed_subpackets=unhashed_subpackets)
        sign_packet = proto.packet(tag=2, blob=signature)
        return subkey_packet + sign_packet

    def sign(self, msg, sign_time=None):
        """Sign GPG message at specified time."""
        if sign_time is None:
            sign_time = int(time.time())

        log.info('signing %d byte message at %s',
                 len(msg), util.time_format(sign_time))
        hashed_subpackets = [proto.subpacket_time(sign_time)]
        unhashed_subpackets = [
            proto.subpacket(16, self.pubkey.key_id())]  # issuer key id

        blob = _make_signature(signer_func=self.conn.sign,
                               data_to_sign=msg,
                               public_algo=self.pubkey.algo_id,
                               hashed_subpackets=hashed_subpackets,
                               unhashed_subpackets=unhashed_subpackets)
        return proto.packet(tag=2, blob=blob)


def _make_signature(signer_func, data_to_sign, public_algo,
                    hashed_subpackets, unhashed_subpackets, sig_type=0):
    # pylint: disable=too-many-arguments
    header = struct.pack('>BBBB',
                         4,         # version
                         sig_type,  # rfc4880 (section-5.2.1)
                         public_algo,
                         8)         # hash_alg (SHA256)
    hashed = proto.subpackets(*hashed_subpackets)
    unhashed = proto.subpackets(*unhashed_subpackets)
    tail = b'\x04\xff' + struct.pack('>L', len(header) + len(hashed))
    data_to_hash = data_to_sign + header + hashed + tail

    log.debug('hashing %d bytes', len(data_to_hash))
    digest = hashlib.sha256(data_to_hash).digest()
    log.info('signing digest: %s', util.hexlify(digest))
    sig = signer_func(digest=digest)

    return bytes(header + hashed + unhashed +
                 digest[:2] +  # used for decoder's sanity check
                 sig)  # actual ECDSA signature


def _split_lines(body, size):
    lines = []
    for i in range(0, len(body), size):
        lines.append(body[i:i+size] + '\n')
    return ''.join(lines)


def armor(blob, type_str):
    """See https://tools.ietf.org/html/rfc4880#section-6 for details."""
    head = '-----BEGIN PGP {}-----\nVersion: GnuPG v2\n\n'.format(type_str)
    body = base64.b64encode(blob)
    checksum = base64.b64encode(util.crc24(blob))
    tail = '-----END PGP {}-----\n'.format(type_str)
    return head + _split_lines(body, 64) + '=' + checksum + '\n' + tail
