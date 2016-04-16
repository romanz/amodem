import struct


def crc24(blob):
    CRC24_INIT = 0xB704CEL
    CRC24_POLY = 0x1864CFBL

    crc = CRC24_INIT
    for octet in bytearray(blob):
        crc ^= (octet << 16)
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= CRC24_POLY
    assert 0 <= crc < 0x1000000
    crc_bytes = struct.pack('>L', crc)
    assert crc_bytes[0] == b'\x00'
    return crc_bytes[1:]
