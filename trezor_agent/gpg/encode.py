"""Create GPG ECDSA signatures and public keys using TREZOR device."""
import logging
import time

from . import decode, keyring, protocol
from .. import factory, formats, util

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

    def pubkey(self, ecdh=False):
        """Return public key as VerifyingKey object."""
        addr = util.get_bip32_address(identity=self.identity, ecdh=ecdh)
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
        return (util.bytes2num(sig[:32]), util.bytes2num(sig[32:]))

    def ecdh(self, pubkey):
        """Derive shared secret using ECDH from remote public key."""
        result = self.client_wrapper.connection.get_ecdh_session_key(
            identity=self.identity,
            peer_public_key=pubkey,
            ecdsa_curve_name=self.curve_name)
        assert len(result.session_key) == 65
        assert result.session_key[:1] == b'\x04'
        return result.session_key

    def close(self):
        """Close the connection to the device."""
        self.client_wrapper.connection.close()


class AgentSigner(object):
    """Sign messages and get public keys using gpg-agent tool."""

    def __init__(self, user_id):
        """Connect to the agent and retrieve required public key."""
        self.sock = keyring.connect_to_agent()
        self.keygrip = keyring.get_keygrip(user_id)

    def sign(self, digest):
        """Sign the digest and return an ECDSA/RSA/DSA signature."""
        return keyring.sign_digest(sock=self.sock,
                                   keygrip=self.keygrip, digest=digest)

    def close(self):
        """Close the connection to gpg-agent."""
        self.sock.close()


def _time_format(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))


def create_primary(user_id, pubkey, signer_func):
    """Export new primary GPG public key, ready for "gpg2 --import"."""
    pubkey_packet = protocol.packet(tag=6, blob=pubkey.data())
    user_id_packet = protocol.packet(tag=13,
                                     blob=user_id.encode('ascii'))

    data_to_sign = (pubkey.data_to_hash() +
                    user_id_packet[:1] +
                    util.prefix_len('>L', user_id.encode('ascii')))
    log.info('creating primary GPG key "%s"', user_id)
    hashed_subpackets = [
        protocol.subpacket_time(pubkey.created),  # signature time
        # https://tools.ietf.org/html/rfc4880#section-5.2.3.7
        protocol.subpacket_byte(0x0B, 9),  # preferred symmetric algo (AES-256)
        # https://tools.ietf.org/html/rfc4880#section-5.2.3.4
        protocol.subpacket_byte(0x1B, 1 | 2),  # key flags (certify & sign)
        # https://tools.ietf.org/html/rfc4880#section-5.2.3.21
        protocol.subpacket_byte(0x15, 8),  # preferred hash (SHA256)
        # https://tools.ietf.org/html/rfc4880#section-5.2.3.8
        protocol.subpacket_byte(0x16, 0),  # preferred compression (none)
        # https://tools.ietf.org/html/rfc4880#section-5.2.3.9
        protocol.subpacket_byte(0x17, 0x80)  # key server prefs (no-modify)
        # https://tools.ietf.org/html/rfc4880#section-5.2.3.17
    ]
    unhashed_subpackets = [
        protocol.subpacket(16, pubkey.key_id()),  # issuer key id
        protocol.CUSTOM_SUBPACKET]

    log.info('confirm signing with primary key')
    signature = protocol.make_signature(
        signer_func=signer_func,
        public_algo=pubkey.algo_id,
        data_to_sign=data_to_sign,
        sig_type=0x13,  # user id & public key
        hashed_subpackets=hashed_subpackets,
        unhashed_subpackets=unhashed_subpackets)

    sign_packet = protocol.packet(tag=2, blob=signature)
    return pubkey_packet + user_id_packet + sign_packet


def create_subkey(primary_bytes, pubkey, signer_func):
    """Export new subkey to GPG primary key."""
    subkey_packet = protocol.packet(tag=14, blob=pubkey.data())
    primary = decode.load_public_key(primary_bytes)
    log.info('adding subkey to primary GPG key "%s"', primary['user_id'])
    data_to_sign = primary['_to_hash'] + pubkey.data_to_hash()

    if pubkey.ecdh:
        embedded_sig = None
    else:
        # Primary Key Binding Signature
        hashed_subpackets = [
            protocol.subpacket_time(pubkey.created)]  # signature time
        unhashed_subpackets = [
            protocol.subpacket(16, pubkey.key_id())]  # issuer key id
        log.info('confirm signing with new subkey')
        embedded_sig = protocol.make_signature(
            signer_func=signer_func,
            data_to_sign=data_to_sign,
            public_algo=pubkey.algo_id,
            sig_type=0x19,
            hashed_subpackets=hashed_subpackets,
            unhashed_subpackets=unhashed_subpackets)

    # Subkey Binding Signature

    # Key flags: https://tools.ietf.org/html/rfc4880#section-5.2.3.21
    # (certify & sign)                   (encrypt)
    flags = (2) if (not pubkey.ecdh) else (4 | 8)

    hashed_subpackets = [
        protocol.subpacket_time(pubkey.created),  # signature time
        protocol.subpacket_byte(0x1B, flags)]

    unhashed_subpackets = []
    unhashed_subpackets.append(protocol.subpacket(16, primary['key_id']))
    if embedded_sig is not None:
        unhashed_subpackets.append(protocol.subpacket(32, embedded_sig))
    unhashed_subpackets.append(protocol.CUSTOM_SUBPACKET)

    log.info('confirm signing with primary key')
    if not primary['_is_custom']:
        signer_func = AgentSigner(primary['user_id']).sign

    signature = protocol.make_signature(
        signer_func=signer_func,
        data_to_sign=data_to_sign,
        public_algo=primary['algo'],
        sig_type=0x18,
        hashed_subpackets=hashed_subpackets,
        unhashed_subpackets=unhashed_subpackets)
    sign_packet = protocol.packet(tag=2, blob=signature)
    return primary_bytes + subkey_packet + sign_packet


def load_from_public_key(pubkey_dict):
    """Load correct public key from the device."""
    user_id = pubkey_dict['user_id']
    created = pubkey_dict['created']
    curve_name = protocol.find_curve_by_algo_id(pubkey_dict['algo'])
    assert curve_name in formats.SUPPORTED_CURVES
    ecdh = (pubkey_dict['algo'] == protocol.ECDH_ALGO_ID)

    conn = HardwareSigner(user_id, curve_name=curve_name)
    pubkey = protocol.PublicKey(
        curve_name=curve_name, created=created,
        verifying_key=conn.pubkey(ecdh=ecdh), ecdh=ecdh)
    assert pubkey.key_id() == pubkey_dict['key_id']
    log.info('%s created at %s for "%s"',
             pubkey, _time_format(pubkey.created), user_id)

    return pubkey, conn
