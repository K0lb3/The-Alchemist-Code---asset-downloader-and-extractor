from enum import IntEnum
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util import Padding
from PIL import Image, ImageOps

a_shared_key = b""


class DecryptOptions(IntEnum):
    None_ = 0
    IsFile = 1
    ExtraKeySaltAT = 2
    ExtraKeySaltATDI = 3


def decrypt(data: bytes, keySalt: str, options: DecryptOptions) -> bytes:
    IV = bytes.fromhex(keySalt) if options == DecryptOptions.IsFile else data[:0x10]

    key = SHA256.SHA256Hash(
        b"".join(
            [
                a_shared_key,
                b"" if options == DecryptOptions.IsFile else keySalt.encode("ascii"),
            ]
        )
    ).digest()[:0x10]

    managed = AES.new(key, iv=IV, mode=AES.MODE_CBC)

    return Padding.unpad(managed.decrypt(data[0x10:]), block_size=0x10, style="pkcs7")


def get_shared_key(texture: Image) -> bytes:
    keyImageAsset = ImageOps.flip(texture)

    bit_count = 0
    index = 0
    num = 0

    key = bytearray(16)
    data = keyImageAsset.tobytes()
    for color_val in data:
        num = (num << 1) + (color_val & 1)
        bit_count += 1

        if bit_count % 8 == 0:
            num = reverse_bits(num)
            if num:
                key[index] = num
                index += 1
            else:
                return key


def reverse_bits(num):
    result = 0
    for _ in range(8):
        result = (result << 1) + (num & 1)
        num >>= 1
    return result
