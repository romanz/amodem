"""Create GPG ECDSA signatures and public keys using TREZOR device."""
import logging
import time

from . import decode, keyring, proto
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
            challenge_visual='',
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
        self.sock = keyring.connect_to_agent()
        self.keygrip = keyring.get_keygrip(user_id)

    def sign(self, digest):
        """Sign the digest and return an ECDSA/RSA/DSA signature."""
        params = keyring.sign_digest(sock=self.sock,
                                     keygrip=self.keygrip, digest=digest)
        return b''.join(proto.mpi(p) for p in params)

    def close(self):
        """Close the connection to gpg-agent."""
        self.sock.close()


def _time_format(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))


class Factory(object):
    """Performs GPG signing operations."""

    def __init__(self, user_id, created, curve_name):
        """Construct and loads a public key from the device."""
        self.user_id = user_id
        assert curve_name in formats.SUPPORTED_CURVES

        self.conn = HardwareSigner(user_id, curve_name=curve_name)
        self.pubkey = proto.PublicKey(
            curve_name=curve_name, created=created,
            verifying_key=self.conn.pubkey())

        log.info('%s created at %s for "%s"',
                 self.pubkey, _time_format(self.pubkey.created), user_id)

    @classmethod
    def from_public_key(cls, pubkey, user_id):
        """Create from an existing GPG public key."""
        s = cls(user_id=user_id,
                created=pubkey['created'],
                curve_name=proto.find_curve_by_algo_id(pubkey['algo']))
        assert s.pubkey.key_id() == pubkey['key_id']
        return s

    def close(self):
        """Close connection and turn off the screen of the device."""
        self.conn.close()

    def create_primary(self):
        """Export new primary GPG public key, ready for "gpg2 --import"."""
        pubkey_packet = proto.packet(tag=6, blob=self.pubkey.data())
        user_id_packet = proto.packet(tag=13,
                                      blob=self.user_id.encode('ascii'))

        data_to_sign = (self.pubkey.data_to_hash() +
                        user_id_packet[:1] +
                        util.prefix_len('>L', self.user_id.encode('ascii')))
        log.info('signing public key "%s"', self.user_id)
        hashed_subpackets = [
            proto.subpacket_time(self.pubkey.created),  # signature time
            # https://tools.ietf.org/html/rfc4880#section-5.2.3.4
            proto.subpacket_byte(0x1B, 1 | 2),  # key flags (certify & sign)
            # https://tools.ietf.org/html/rfc4880#section-5.2.3.21
            proto.subpacket_byte(0x15, 8),  # preferred hash (SHA256)
            # https://tools.ietf.org/html/rfc4880#section-5.2.3.8
            proto.subpacket_byte(0x16, 0),  # preferred compression (none)
            # https://tools.ietf.org/html/rfc4880#section-5.2.3.9
            proto.subpacket_byte(0x17, 0x80)  # key server prefs (no-modify)
            # https://tools.ietf.org/html/rfc4880#section-5.2.3.17
        ]
        unhashed_subpackets = [
            proto.subpacket(16, self.pubkey.key_id()),  # issuer key id
            proto.CUSTOM_SUBPACKET]

        signature = proto.make_signature(
            signer_func=self.conn.sign,
            public_algo=self.pubkey.algo_id,
            data_to_sign=data_to_sign,
            sig_type=0x13,  # user id & public key
            hashed_subpackets=hashed_subpackets,
            unhashed_subpackets=unhashed_subpackets)

        sign_packet = proto.packet(tag=2, blob=signature)
        return pubkey_packet + user_id_packet + sign_packet

    def create_subkey(self, primary_bytes):
        """Export new subkey to `self.user_id` GPG primary key."""
        subkey_packet = proto.packet(tag=14, blob=self.pubkey.data())
        primary = decode.load_public_key(primary_bytes)
        log.info('adding subkey to primary GPG key "%s" (%s)',
                 self.user_id, util.hexlify(primary['key_id']))
        data_to_sign = primary['_to_hash'] + self.pubkey.data_to_hash()

        # Primary Key Binding Signature
        hashed_subpackets = [
            proto.subpacket_time(self.pubkey.created)]  # signature time
        unhashed_subpackets = [
            proto.subpacket(16, self.pubkey.key_id())]  # issuer key id
        log.info('confirm signing subkey with hardware device')
        embedded_sig = proto.make_signature(
            signer_func=self.conn.sign,
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
        signature = proto.make_signature(
            signer_func=gpg_agent.sign,
            data_to_sign=data_to_sign,
            public_algo=primary['algo'],
            sig_type=0x18,
            hashed_subpackets=hashed_subpackets,
            unhashed_subpackets=unhashed_subpackets)
        sign_packet = proto.packet(tag=2, blob=signature)
        return primary_bytes + subkey_packet + sign_packet

    def sign_message(self, msg, sign_time=None):
        """Sign GPG message at specified time."""
        if sign_time is None:
            sign_time = int(time.time())

        log.info('signing %d byte message at %s',
                 len(msg), _time_format(sign_time))
        hashed_subpackets = [proto.subpacket_time(sign_time)]
        unhashed_subpackets = [
            proto.subpacket(16, self.pubkey.key_id())]  # issuer key id

        blob = proto.make_signature(
            signer_func=self.conn.sign,
            data_to_sign=msg,
            public_algo=self.pubkey.algo_id,
            hashed_subpackets=hashed_subpackets,
            unhashed_subpackets=unhashed_subpackets)
        return proto.packet(tag=2, blob=blob)
