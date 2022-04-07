import zipfile
import io
import UnityPy
from .encryption_helper import get_shared_key
from .qooapp import download_QooApp_apk
from .versions import Version
from .paths import RES
from typing import Tuple
import os

# TypeTree of the ScriptableTexture2D MonoBehaviour that refers to the Texture2D
# that contains the shared key encoded into the texture via LSB
ScriptableTexture2D = [
    {"level": 0, "type": "MonoBehaviour", "name": "Base", "meta_flag": 0},
    {"level": 1, "type": "PPtr<GameObject>", "name": "m_GameObject", "meta_flag": 0},
    {"level": 2, "type": "int", "name": "m_FileID", "meta_flag": 0},
    {"level": 2, "type": "SInt64", "name": "m_PathID", "meta_flag": 0},
    {"level": 1, "type": "UInt8", "name": "m_Enabled", "meta_flag": 16384},
    {"level": 1, "type": "PPtr<MonoScript>", "name": "m_Script", "meta_flag": 0},
    {"level": 2, "type": "int", "name": "m_FileID", "meta_flag": 0},
    {"level": 2, "type": "SInt64", "name": "m_PathID", "meta_flag": 0},
    {"level": 1, "type": "string", "name": "m_Name", "meta_flag": 0},
    {"level": 2, "type": "Array", "name": "Array", "meta_flag": 16384},
    {"level": 3, "type": "int", "name": "size", "meta_flag": 0},
    {"level": 3, "type": "char", "name": "data", "meta_flag": 0},
    {"level": 1, "type": "PPtr<Texture2D>", "name": "texture", "meta_flag": 0},
    {"level": 2, "type": "int", "name": "m_FileID", "meta_flag": 0},
    {"level": 2, "type": "SInt64", "name": "m_PathID", "meta_flag": 0},
]


def get_version_consts_fp(version: Version) -> str:
    os.makedirs(RES, exist_ok=True)
    return os.path.join(RES, f"consts_{version.name}.bin")


def load_version_consts(version: Version) -> Tuple[str, bytes]:
    settings_fp = get_version_consts_fp(version)
    if os.path.exists(settings_fp):
        with open(settings_fp, "rb") as f:
            network_ver, shared_key = f.read().split(b"\r\n")
        network_ver = network_ver.decode("utf8")
        return network_ver, shared_key
    else:
        return update_version_consts(version)


def update_version_consts(version: Version) -> Tuple[str, bytes]:
    print("updating app consts")
    settings_fp = get_version_consts_fp(version)
    network_ver, shared_key = get_new_version(version.package_id)
    with open(settings_fp, "wb") as f:
        f.write(network_ver.encode("utf8"))
        f.write(b"\r\n")
        f.write(shared_key)
    return network_ver, shared_key


def get_new_version(package_id: str) -> Tuple[str, bytes]:
    # download & save latest apk from QooAp
    #apk_data = download_QooApp_apk(package_id)
    apk_data = download_apksupport(package_id)
    return extract_version(apk_data)


def extract_version(apk_data: bytes) -> Tuple[str, bytes]:
    # extract the version
    apk_buf = io.BytesIO(apk_data)
    zip = zipfile.ZipFile(apk_buf)

    network_ver = None
    shared_key = None

    for f in zip.namelist():
        if f[:16] == "assets/bin/Data/":
            zip_file = zip.open(f)
            env = UnityPy.load(zip_file)
            objs = env.objects
            for obj in objs:
                if obj.type.name == "TextAsset":
                    data = obj.read()
                    if data.name == "networkver":
                        network_ver = data.text
                        break

            for obj in objs:
                if obj.type.name == "MonoBehaviour":
                    data = obj.read()
                    if data.name == "ScriptableTexture2D":
                        data.read_typetree(ScriptableTexture2D)
                        if data.texture:  # JP
                            texture = data.texture.read().image
                        else:  # Global
                            ext_name = data.assets_file.externals[
                                data.texture.file_id - 1
                            ].name
                            with zip.open(f"assets/bin/Data/{ext_name}") as zip_file2:
                                env2 = UnityPy.load(zip_file2)
                                texture = (
                                    env2.files["0"]
                                    .objects[data.texture.path_id]
                                    .read()
                                    .image
                                )
                        shared_key = get_shared_key(texture)
                        break

            zip_file.close()

    zip.close()
    apk_buf.close()

    return network_ver, bytes(shared_key)

def download_apksupport(appid: str) -> bytes:
    from urllib.request import Request, urlopen
    import re
    data = urlopen(Request(url=f"https://apk.support/download-app/{appid}", headers = {"user-agent":"Firefox"})).read()
    apk_url = re.search(r'href="(https://fastp.+?)">', data.decode("utf-8")).group(1)
    return urlopen(apk_url).read()
