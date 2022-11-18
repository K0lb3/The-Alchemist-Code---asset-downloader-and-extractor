import zipfile
import io
import UnityPy
from .encryption_helper import get_shared_key
from .qooapp import download_QooApp_apk
from .versions import Version
from .paths import RES
from typing import Tuple
import os

import requests

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
    # apk_data = download_QooApp_apk(package_id)
    apk_data = download_apksupport(package_id)
    return extract_version(apk_data)


def extract_version(apk_data: bytes) -> Tuple[str, bytes]:
    # extract the version
    apk_buf = io.BytesIO(apk_data)
    zip = zipfile.ZipFile(apk_buf)

    network_ver = None
    shared_key = None
    # check if xapk
    for x in zip.namelist():
        if x.endswith(".apk") and not x.startswith("config."):
            with zip.open(x) as f:
                network_ver, shared_key = extract_version(f.read())
            break
    if network_ver and shared_key:
        zip.close()
        apk_buf.close()
        return network_ver, shared_key

    env = UnityPy.Environment()
    for f in zip.namelist():
        env.load_file(zip.open(f), env, os.path.basename(f))

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.name == "networkver":
                network_ver = data.text
                break

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            data = obj.read()
            if data.name == "ScriptableTexture2D":
                data.read_typetree(ScriptableTexture2D)
                if data.texture:  # JP
                    texture = data.texture.read().image
                else:  # Global
                    ext_name = data.assets_file.externals[data.texture.file_id - 1].name
                    with zip.open(f"assets/bin/Data/{ext_name}") as zip_file2:
                        env2 = UnityPy.load(zip_file2)
                        texture = (
                            env2.files["0"].objects[data.texture.path_id].read().image
                        )
                shared_key = get_shared_key(texture)
                break

    zip.close()
    apk_buf.close()

    return network_ver, bytes(shared_key)


def download_apksupport(appid: str) -> bytes:
    from urllib.request import Request, urlopen
    from urllib.parse import quote
    import re

    html = requests.post(
        url=f"https://apk.support/download-app/{appid}",
        data=f"cmd=apk&pkg={appid}&arch=default&tbi=default&device_id=&model=default&language=en&dpi=480&av=default".encode(
            "utf8"
        ),
        headers={
            "sec-ch-ua": '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            "sec-ch-ua-platform": "Windows",
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
            "accept": "*/*",
            "origin": "https://apk.support",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            f"referer": "https://apk.support/download-app/{appid}",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "content-length": "112",
            "content-type": "application/x-www-form-urlencoded",
        },
    ).text
    apks = re.findall(
        r"""<a rel="nofollow" href="(.+?.apk)">\s+?<span class.+?</span>(.+?.apk)</span>""",
        html,
    )
    for apk_url, apk_name in apks:
        if "config" not in apk_name:
            return requests.get(apk_url).content
    else:
        raise Exception("couldn't find base apk found")
