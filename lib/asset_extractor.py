from collections import Counter
import json
import os
import zlib
import UnityPy
from .assetlist import AssetBundleFlags, AssetListItem

def extract_asset(dst: str, data: bytes, item:AssetListItem) -> None:
    if AssetBundleFlags.Scene & item.Flags:
        fp = os.path.join(dst, "Scene", *item.Path.split("/"))
    else:
        fp = os.path.join(dst, *item.Path.split("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)

    if AssetBundleFlags.IsCombined & item.Flags:
        return

    if AssetBundleFlags.Compressed & item.Flags:
        data = zlib.decompress(data)
    

    if AssetBundleFlags.RawData & item.Flags:
        fp = os.path.join(dst, item.Path)
        
        
        if not AssetBundleFlags.StreamingAsset & item.Flags:
            if (data[:1] == b'{' and data[-1:] == b'}') or (data[:1] == b'[' and data[-1:] == b']'):
                fp += ".json"
            else:
                fp += ".txt"
        
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as f:
            f.write(data)
    
    else:
        env = UnityPy.load(data)
        objs = env.objects
        expotable_objs = sorted((obj for obj in objs if obj.type.name in TYPES), key = lambda x:x.type.name)
        if len(objs) == 2: # one of them is an AssetBundle
            export_obj(expotable_objs[0], fp, False)
        elif len(objs) == 3 and len(expotable_objs) == 2 and expotable_objs[0].type.name == "Sprite" and expotable_objs[1].type.name == "Texture2D":
            export_obj(expotable_objs[0], fp, False)
        else:
            extracted = []
            for obj in expotable_objs:
                if obj.path_id not in extracted:
                    extracted.extend(export_obj(
                        obj, fp, append_name=True
                    ))

TYPES = [
    # Images
    'Sprite',
    'Texture2D',
    # Text (filish)
    'TextAsset',
    'Shader',
    'MonoBehaviour',
    'Mesh'
    # Font
    'Font',
    # Audio
    'AudioClip',
]

def export_obj(obj, fp: str, append_name: bool = False) -> list:
    if obj.type not in TYPES:
        return []

    data = obj.read()
    if append_name:
        fp = os.path.join(fp, data.name)

    fp, extension = os.path.splitext(fp)
    os.makedirs(os.path.dirname(fp), exist_ok=True)

    # streamlineable types
    export = None
    if obj.type == 'TextAsset':
        if not extension:
            extension = '.txt'
        export = data.script

    elif obj.type == "Font":
        if data.m_FontData:
            extension = ".ttf"
            if data.m_FontData[0:4] == b"OTTO":
                extension = ".otf"
            export = data.m_FontData
        else:
            return [obj.path_id]

    elif obj.type == "Mesh":
        extension = ".obf"
        export = data.export().encode("utf8")

    elif obj.type == "Shader":
        extension = ".txt"
        export = data.export().encode("utf8")

    elif obj.type == "MonoBehaviour":
        # The data structure of MonoBehaviours is custom
        # and is stored as nodes
        # If this structure doesn't exist,
        # it might still help to at least save the binary data,
        # which can then be inspected in detail.
        if obj.serialized_type.nodes:
            extension = ".json"
            export = json.dumps(
                obj.read_typetree(),
                indent=4,
                ensure_ascii=False
            ).encode("utf8")
        else:
            extension = ".bin"
            export = data.raw_data

    if export:
        with open(f"{fp}{extension}", "wb") as f:
            f.write(export)

    # non-streamlineable types
    if obj.type == "Sprite":
        data.image.save(f"{fp}.png")

        return [obj.path_id, data.m_RD.texture.path_id, getattr(data.m_RD.alphaTexture, 'path_id', None)]

    elif obj.type == "Texture2D":
        if not os.path.exists(fp) and data.m_Width:
            # textures can have size 0.....
            data.image.save(f"{fp}.png")

    elif obj.type == "AudioClip":
        samples = data.samples
        if len(samples) == 0:
            pass
        elif len(samples) == 1:
            with open(f"{fp}.wav", "wb") as f:
                f.write(list(data.samples.values())[0])
        else:
            os.makedirs(fp, exist_ok=True)
            for name, clip_data in samples.items():
                with open(os.path.join(fp, f"{name}.wav"), "wb") as f:
                    f.write(clip_data)
    return [obj.path_id]
