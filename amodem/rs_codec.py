import itertools


class RSCodecProvider:
    _codec = None
    _current_num_symbols = None
    _expect_num_symbols = 32

    @classmethod
    def get_num_symbols(cls):
        return cls._expect_num_symbols

    @classmethod
    def set_num_symbols(cls, num_symbols: int):
        cls._expect_num_symbols = num_symbols

    @classmethod
    def get_codec(cls):
        """
        Get or create a Reed-Solomon encoder instance.
        If num_symbols is different from the currently cached encoder, create a new encoder.
        """
        if cls._codec is None or cls._current_num_symbols != cls._expect_num_symbols:
            import reedsolo
            cls._current_num_symbols = cls._expect_num_symbols
            cls._codec = reedsolo.RSCodec(cls._current_num_symbols)
        return cls._codec


def encode_with_rs(data):
    # Ensure the data is of bytearray type
    if not isinstance(data, bytearray):
        data = bytearray(data)
    encoded = RSCodecProvider.get_codec().encode(data)
    return encoded


def decode_with_rs(encoded_data):
    try:
        decoded, _, _ = RSCodecProvider.get_codec().decode(encoded_data)
        return decoded
    except Exception:
        # import traceback
        # traceback.print_exc()
        return encoded_data


def encrypt_pack(data):
    return encode_with_rs(data)


def decrypt_pack(encoded_data, chunk_size):
    chunk = bytearray(itertools.islice(encoded_data, chunk_size))
    if len(chunk) < chunk_size:
        raise ValueError(f'Incomplete frame, length {len(chunk)} < {chunk_size}(required)')

    decoded = decode_with_rs(chunk)
    return iter(decoded)
