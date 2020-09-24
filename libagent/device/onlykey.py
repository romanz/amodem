# pylint: disable=too-many-locals,too-many-statements,too-many-branches
# pylint: disable=attribute-defined-outside-init
"""OnlyKey-related code (see https://www.onlykey.io/)."""

import logging
import hashlib
import codecs
import time
import ecdsa
import nacl.signing
import unidecode

from . import interface

# import pgpy
# from pgpy import PGPKey


log = logging.getLogger(__name__)


class OnlyKey(interface.Device):
    """Connection to OnlyKey device."""

    @classmethod
    def package_name(cls):
        """Python package name (at PyPI)."""
        return 'onlykey-agent'

    @property
    def _defs(self):
        from . import onlykey_defs
        return onlykey_defs

    def connect(self):
        """Enumerate and connect to the first USB HID interface."""
        try:
            self.device_name = 'OnlyKey'
            self.ok = self._defs.OnlyKey()
            self.ok.set_time(time.time())
            self.okversion = self.ok.read_string(timeout_ms=500)
            self.okversion = self.okversion[8:]
            self.skeyslot = 132
            self.dkeyslot = 132
        except Exception as e:
            raise interface.NotFoundError('{} not connected: "{}"') from e

    def set_skey(self, skey):
        """Set signing key to use."""
        self.skeyslot = skey
        log.debug('Setting skey slot = %s', skey)

    def set_dkey(self, dkey):
        """Set decryption key to use."""
        self.dkeyslot = dkey
        log.debug('Setting dkey slot = %s', dkey)

    def import_pub(self, pubkey):
        """Import PGP public key."""
        self.import_pubkey = pubkey
        log.debug('Public key to import = %s', pubkey)
        # self.import_pubkey_obj, _ = pgpy.PGPKey.from_blob(pubkey)
        # self.import_pubkey_bytes = bytes(self.import_pubkey_obj)

    def get_sk_dk(self):
        """Get default signing key and decryption key slots."""
        self.set_skey(132)
        self.set_dkey(132)

    def sig_hash(self, sighash):
        """Set signature hashing algorithm to use."""
        if sighash in (b'rsa-sha2-512', b'rsa-sha2-256'):
            self.sighash = sighash
            log.info('Setting RSA signature Hash Type =%s', sighash)

    def close(self):
        """Close connection."""
        log.info('disconnected from %s', self.device_name)
        self.ok.close()

    def pubkey(self, identity, ecdh=False):
        """Return public key."""
        curve_name = identity.get_curve_name(ecdh=ecdh)
        if identity.identity_dict['proto'] != 'ssh' and hasattr('self', 'skeyslot') is False:
            self.get_sk_dk()
        if identity.identity_dict['proto'] != 'ssh' and self.dkeyslot < 132 and ecdh is True:
            this_slot_id = self.dkeyslot
            log.info('Key Slot =%s', this_slot_id)
        elif self.skeyslot < 132 and ecdh is False:
            this_slot_id = self.skeyslot
            log.info('Key Slot =%s', this_slot_id)
        else:
            this_slot_id = 132

        log.info('Requesting public key from key slot =%s', this_slot_id)

        log.debug('"%s" getting public key (%s) from %s',
                  identity.to_string(), curve_name, self)

        # Calculate hash for key derivation input data
        if identity.identity_dict['proto'] == 'ssh':
            if identity.identity_dict.get('user'):
                id_parts = unidecode.unidecode(identity.identity_dict['user'] + '@' +
                                               identity.identity_dict['host']).encode('ascii')
            else:
                id_parts = unidecode.unidecode(identity.identity_dict['host']).encode('ascii')
        else:
            id_parts = identity.to_bytes()
        log.info('Identity to hash =%s', id_parts)
        h1 = hashlib.sha256()
        h1.update(id_parts)
        data = h1.hexdigest()
        log.info('Identity hash =%s', data)

        if this_slot_id > 100:
            if curve_name == 'curve25519':
                data = '04' + data
            elif curve_name == 'secp256k1':
                # Not currently supported by agent, for future use
                data = '03' + data
            elif curve_name == 'nist256p1':
                data = '02' + data
            elif curve_name == 'ed25519':
                data = '01' + data
        else:
            data = '00' + data

        self.ok.send_message(msg=self._defs.Message.OKGETPUBKEY, slot_id=this_slot_id, payload=data)
        log.info('curve name= %s', repr(curve_name))
        t_end = time.time() + 1.5
        if curve_name != 'rsa':
            while time.time() < t_end:
                try:
                    ok_pubkey = self.ok.read_bytes(timeout_ms=100)
                    if len(ok_pubkey) == 64 and len(set(ok_pubkey[0:63])) != 1:
                        break
                except Exception as e:
                    raise interface.DeviceError(e)

            log.info('received= %s', repr(ok_pubkey))
            if len(set(ok_pubkey[34:63])) == 1:
                if curve_name in ('nist256p1', 'secp256k1'):
                    raise interface.DeviceError("Public key curve does not match requested type")
                ok_pubkey = bytearray(ok_pubkey[0:32])
                log.info('Received Public Key generated by OnlyKey= %s', repr(ok_pubkey.hex()))
                vk = nacl.signing.VerifyKey(bytes(ok_pubkey),
                                            encoder=nacl.encoding.RawEncoder)
                log.info('vk= %s', repr(vk))
                # time.sleep(3)
                return vk
            elif len(ok_pubkey) == 64:
                ok_pubkey = bytearray(ok_pubkey[0:64])
                if curve_name in ('ed25519', 'curve25519'):
                    raise interface.DeviceError("Public key curve does not match requested type")
                log.info('Received Public Key generated by OnlyKey= %s', repr(ok_pubkey))
                if identity.curve_name == 'nist256p1':
                    vk = ecdsa.VerifyingKey.from_string(ok_pubkey, curve=ecdsa.NIST256p)
                else:
                    vk = ecdsa.VerifyingKey.from_string(ok_pubkey, curve=ecdsa.SECP256k1)
                return vk
        else:
            ok_pubkey = []
            while time.time() < t_end:
                try:
                    ok_pub_part = self.ok.read_bytes(timeout_ms=100)
                    if len(ok_pub_part) == 64 and len(set(ok_pub_part[0:63])) != 1:
                        log.info('received part= %s', repr(ok_pub_part))
                        ok_pubkey += ok_pub_part
                        # Todo know RSA type to know how many packets
                except Exception as e:
                    raise interface.DeviceError(e)

            log.info('received= %s', repr(ok_pubkey))
            if len(ok_pubkey) == 256:
                # https://security.stackexchange.com/questions/42268/how-do-i-get-the-rsa-bit-length-with-the-pubkey-and-openssl
                ok_pubkey = b'\x00\x00\x00\x07' + b'\x73\x73\x68\x2d\x72\x73\x61' + \
                                                b'\x00\x00\x00\x03' + b'\x01\x00\x01' + \
                                                b'\x00\x00\x01\x01' + b'\x00' + bytes(ok_pubkey)
                # ok_pubkey = b'\x00\x00\x00\x07' + b'\x72\x73\x61\x2d\x73\x68\x61\x32\x2d\x32\x35\x
                # 36' + b'\x00\x00\x00\x03' + b'\x01\x00\x01' + b'\x00\x00\x01\x01' + b'\x00' + byte
                # s(ok_pubkey)
            elif len(ok_pubkey) == 512:
                ok_pubkey = b'\x00\x00\x00\x07' + b'\x73\x73\x68\x2d\x72\x73\x61' + \
                                                b'\x00\x00\x00\x03' + b'\x01\x00\x01' + \
                                                b'\x00\x00\x02\x01' + b'\x00' + bytes(ok_pubkey)
            else:
                raise interface.DeviceError("Error response length is not a valid public key")
            log.info('pubkey len = %s', len(ok_pubkey))
            return ok_pubkey

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        curve_name = identity.get_curve_name(ecdh=False)
        log.debug('"%s" signing %r (%s) on %s',
                  identity.to_string(), blob, curve_name, self)
        if identity.identity_dict['proto'] != 'ssh' and hasattr('self', 'skeyslot') is False:
            self.get_sk_dk()
        # Calculate hash for SSH signing
        if curve_name == 'rsa':
            if self.sighash == b'rsa-sha2-512':
                log.info('rsa-sha2-512')
                h1 = hashlib.sha512()
                h1.update(blob)
                data = h1.hexdigest()
                data = codecs.decode(data, 'hex_codec')
            elif self.sighash == b'rsa-sha2-256':
                log.info('rsa-sha2-256')
                h1 = hashlib.sha256()
                h1.update(blob)
                data = h1.hexdigest()
                data = codecs.decode(data, 'hex_codec')
        else:
            # Calculate hash for key derivation input data
            h1 = hashlib.sha256()
            if identity.identity_dict['proto'] == 'ssh':
                if identity.identity_dict.get('user'):
                    id_parts = unidecode.unidecode(identity.identity_dict['user'] + '@' +
                                                   identity.identity_dict['host']).encode('ascii')
                else:
                    id_parts = unidecode.unidecode(identity.identity_dict['host']).encode('ascii')
            else:
                id_parts = identity.to_bytes()
            h1.update(id_parts)
            data = h1.hexdigest()
            data = codecs.decode(data, 'hex_codec')
            log.info('Identity to hash =%s', id_parts)
            log.info('Identity hash =%s', data)
        # Determine type of key to derive on OnlyKey for signature
        # Slot 132 used for derived key, slots 101-116 used for stored ecc keys
        # slots 1-4 used for stored RSA keys
        if self.skeyslot == 132:
            if curve_name == 'ed25519':
                this_slot_id = 201
                log.info('Key type ed25519')
            elif curve_name == 'nist256p1':
                this_slot_id = 202
                log.info('Key type nistp256')
            else:
                this_slot_id = 203
                log.info('Key type secp256k1')
            # Send data and identity hash
            raw_message = blob + data
        else:
            this_slot_id = self.skeyslot
            # Send just data to sign
            raw_message = blob
        h2 = hashlib.sha256()
        h2.update(raw_message)
        d = h2.digest()
        assert len(d) == 32
        b1, b2, b3 = get_button(self, d[0]), get_button(self, d[15]), get_button(self, d[31])
        log.info('Key Slot =%s', this_slot_id)
        print('Enter the 3 digit challenge code on OnlyKey to authorize '+identity.to_string())
        print('{} {} {}'.format(b1, b2, b3))
        t_end = time.time() + 22
        if curve_name != 'rsa':
            self.ok.send_large_message2(msg=self._defs.Message.OKSIGN, payload=raw_message,
                                        slot_id=this_slot_id)
            while time.time() < t_end:
                try:
                    result = self.ok.read_bytes(timeout_ms=100)
                    if len(result) == 64 and len(set(result[0:63])) != 1:
                        break
                except Exception as e:
                    raise interface.DeviceError(e)

            if len(result) >= 60:
                log.info('received= %s', repr(result))
                while len(result) < 64:
                    result.append(0)
                log.info('disconnected from %s', self.device_name)
                self.ok.close()
                return bytes(result)
        else:
            self.ok.send_large_message2(msg=self._defs.Message.OKSIGN, payload=data,
                                        slot_id=this_slot_id)
            result = []
            while time.time() < t_end:
                try:
                    sig_part = self.ok.read_bytes(timeout_ms=100)
                    if len(sig_part) == 64 and len(set(sig_part[0:63])) != 1:
                        log.info('received part= %s', repr(sig_part))
                        result += sig_part
                        t_end = time.time() + 1
                        # Todo know RSA type to know how many packets
                except Exception as e:
                    raise interface.DeviceError(e)

            log.info('received= %s', repr(result))
            return bytes(result)
        raise Exception('failed to sign challenge')

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        curve_name = identity.get_curve_name(ecdh=True)
        log.debug('"%s" shared session key (%s) for %r from %s',
                  identity.to_string(), curve_name, pubkey, self)
        # Calculate hash for key derivation input data
        h1 = hashlib.sha256()
        if identity.identity_dict['proto'] == 'ssh':
            if identity.identity_dict.get('user'):
                id_parts = unidecode.unidecode(identity.identity_dict['user'] + '@' +
                                               identity.identity_dict['host']).encode('ascii')
            else:
                id_parts = unidecode.unidecode(identity.identity_dict['host']).encode('ascii')
        else:
            id_parts = identity.to_bytes()
        h1.update(id_parts)
        log.info('Identity to hash =%s', id_parts)
        data = h1.hexdigest()
        log.info('Identity hash =%s', data)
        data = codecs.decode(data, 'hex_codec')
        # Determine type of key to derive on OnlyKey for ecdh
        # Slot 132 used for derived key, slots 101-116 used for stored ecc keys,
        # slots 1-4 used for stored RSA keys
        if self.dkeyslot == 132:
            if curve_name == 'curve25519':
                this_slot_id = 204
                log.info('Key type curve25519')
            elif curve_name == 'nist256p1':
                this_slot_id = 202
                log.info('Key type nistp256')
            else:
                this_slot_id = 203
                log.info('Key type secp256k1')
            raw_message = pubkey + data
        else:
            this_slot_id = self.dkeyslot
            raw_message = pubkey
        log.info('Key Slot =%s', this_slot_id)
        log.info('data hash =%s', data)
        h2 = hashlib.sha256()
        h2.update(raw_message)
        d = h2.digest()
        assert len(d) == 32
        b1, b2, b3 = get_button(self, d[0]), get_button(self, d[15]), get_button(self, d[31])
        self.ok.send_large_message2(msg=self._defs.Message.OKDECRYPT, payload=raw_message,
                                    slot_id=this_slot_id)
        print('Enter the 3 digit challenge code on OnlyKey to authorize ' + identity.to_string())
        print('{} {} {}'.format(b1, b2, b3))
        t_end = time.time() + 22
        if curve_name != 'rsa':
            while time.time() < t_end:
                try:
                    result = self.ok.read_bytes(timeout_ms=100)
                    if len(result) == 64 and len(set(result[0:63])) != 1:
                        break
                except Exception as e:
                    raise interface.DeviceError(e)
            if len(set(result[34:63])) == 1:
                result = b'\x04' + bytes(result[0:32])
        else:
            result = []
            while time.time() < t_end:
                try:
                    dec_part = self.ok.read_bytes(timeout_ms=100)
                    if len(dec_part) == 64 and len(set(dec_part[0:63])) != 1:
                        log.info('received part= %s', repr(dec_part))
                        result += dec_part
                        t_end = time.time() + 1
                        # Todo know RSA type to know how many packets
                except Exception as e:
                    raise interface.DeviceError(e)

        log.info('received= %s', repr(result))
        log.info('disconnected from %s', self.device_name)
        self.ok.close()
        return bytes(result)


def get_button(self, byte):
    """Return button number."""
    if str(self.okversion) == 'v0.2-beta.8c':
        return byte % 5 + 1
    else:
        return byte % 6 + 1
