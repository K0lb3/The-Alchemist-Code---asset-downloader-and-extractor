import io
import os
import struct
from collections import namedtuple
from enum import IntFlag
from typing import List


def readInt32(fh):
    return struct.unpack("i", fh.read(4))[0]


def readUInt32(fh):
    return struct.unpack("I", fh.read(4))[0]


def read7BitEncodedInt(fh):  # aka varint
    num = 0
    num2 = 0
    while num2 != 35:
        b = fh.read(1)[0]
        num |= b & 127 << num2
        num2 += 7
        if (b & 128) == 0:
            return num
    raise NotImplementedError()


def readString(fh):
    num = 0
    num2 = read7BitEncodedInt(fh)
    if num2 == 0:
        return ""
    chars = 0
    sb = []
    while True:
        count = min(num2 - num, 128)
        chars_raw = fh.read(count)
        chars = chars_raw.decode("utf8")
        num3 = len(chars_raw)
        if num3 == 0:
            raise EOFError()
        if num == 0 and num3 == num2:
            return chars
        sb.append(chars)
        num += num3
        if num >= num2:
            return "".join(sb)


class AssetBundleFlags(IntFlag):
    Compressed = 1
    RawData = 2
    Required = 4
    Scene = 8
    Tutorial = 16
    Multiplay = 32
    StreamingAsset = 64
    TutorialMovie = 128
    Persistent = 256
    DiffAsset = 512
    iOSRequire = 1024
    Home = 2048
    IsLanguage = 4096
    IsCombined = 8192
    IsFolder = 16384

    def dump(self) -> str:
        return [flag.name for flag in AssetBundleFlags if flag in self]


AssetListItem = namedtuple(
    "Item",
    "ID,Size,CompressedSize,Path,PathHash,Hash,Flags,Dependencies,AdditionalDependencies,AdditionalStreamingAssets",
)


class AssetList:
    # original
    mRevision: int
    mItems: List[AssetListItem]
    # AssetsPrefix: str = "Assets/"
    # ResourcesPrefix: str = "Assets/Resources/"
    # StreamingAssetsPrefix: str = "Assets/StreamingAssets/"

    def __init__(self, reader=None) -> None:
        self.mItems = []
        if reader:
            if isinstance(reader, (bytes, bytearray)):
                reader = io.BytesIO(reader)
            elif isinstance(reader, str) and os.path.exists(reader):
                with open(reader, "rb") as f:
                    reader = io.BytesIO(f.read())
            elif hasattr(reader, "read"):
                pass
            else:
                raise NotImplementedError("don't know how to handle this reader input")
            self.read(reader)

    def read(self, reader):
        if isinstance(reader, str):
            reader = open(reader, "rb")

        self.mRevision = readInt32(reader)

        self.mItems = [
            AssetListItem(
                ID=readUInt32(reader),
                # IDStr = item.ID.ToString("X8").ToLower(),
                Size=readInt32(reader),
                CompressedSize=readInt32(reader),
                Path=readString(reader),
                PathHash=readInt32(reader),
                Hash=readUInt32(reader),
                Flags=AssetBundleFlags(readUInt32(reader)),
                Dependencies=[readInt32(reader) for _ in range(readUInt32(reader))],
                AdditionalDependencies=[
                    readInt32(reader) for _ in range(readUInt32(reader))
                ],
                AdditionalStreamingAssets=[
                    readInt32(reader) for _ in range(readUInt32(reader))
                ],
            )
            for _ in range(readInt32(reader))
        ]

    def to_dict(self) -> dict:
        return {
            "mRevision": self.mRevision,
            "mItems": [
                {
                    "IDStr" : f"{item.ID:08x}",
                    **{
                        key: val if not isinstance(val, AssetBundleFlags) else val.dump()
                        for key, val in item._asdict().items()
                    }
                }
                for item in self.mItems
            ],
        }
