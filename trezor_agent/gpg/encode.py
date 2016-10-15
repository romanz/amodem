"""Create GPG ECDSA signatures and public keys using TREZOR device."""
import logging
import time

from . import decode, device, keyring, protocol
from .. import util

log = logging.getLogger(__name__)


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
        signer_func = keyring.create_agent_signer(primary['user_id'])

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
    log.debug('pubkey_dict: %s', pubkey_dict)
    user_id = pubkey_dict['user_id']
    created = pubkey_dict['created']
    curve_name = protocol.get_curve_name_by_oid(pubkey_dict['curve_oid'])
    ecdh = (pubkey_dict['algo'] == protocol.ECDH_ALGO_ID)

    conn = device.HardwareSigner(user_id, curve_name=curve_name)
    pubkey = protocol.PublicKey(
        curve_name=curve_name, created=created,
        verifying_key=conn.pubkey(ecdh=ecdh), ecdh=ecdh)
    assert pubkey.key_id() == pubkey_dict['key_id']
    log.info('%s created at %s for "%s"',
             pubkey, _time_format(pubkey.created), user_id)

    return pubkey, conn
