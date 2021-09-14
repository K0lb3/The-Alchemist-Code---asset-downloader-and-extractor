from urllib.request import Request, urlopen
import json, msgpack

from .encryption_helper import decrypt, DecryptOptions


# def req_asset_old(host_dl: str, version: str, typ: str, name: str) -> bytes:
#     # request asset list
#     url = "{host_dl}/assets/{version}/{typ}/{name}".format(
#         host_dl=host_dl, version=version, typ=typ, name=name
#     )
#     asset = urlopen(url, timeout=1000).read()
#     return asset
def req_asset(url:str, asset_id: str) -> bytes:
    # request asset list
    item_url = f"{url}/{asset_id}"
    try:
        asset = urlopen(item_url, timeout=60).read()
    except ConnectionResetError:
        print("ConnectionResetError while trying to download", item_url)
        return req_asset(url, asset_id)
    except Exception as e:
        input()
    return asset

def req_chkver2(api: str, network_ver: str) -> dict:
    req = Request(
        url=f"https://{api}/chkver2",
        data=json.dumps({"ver": network_ver}).encode("utf8"),
        headers={
            "Content-Type": "application/octet-stream+jhotuhiahanoatuhinga+fakamunatanga",
            "X-Unity-Version": "2020.3.16f1",
            "Accept-Encoding": "identity",
            "Content-Encoding": "identity",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.1.1; SM-G965N Build/LYZ28N)",
        },
        method="POST",
    )
    res = urlopen(req)
    data = decrypt_payload(res)
    return data


def decrypt_payload(response) -> bytes:
    content_type = response.headers["Content-Type"]
    options = DecryptOptions.ExtraKeySaltATDI
    if EncodingTypes.BCT_NO_EXTRA_KEY_SALT in content_type:
        content_type = content_type.replace(
            f"+{EncodingTypes.BCT_NO_EXTRA_KEY_SALT}", ""
        )
        options = DecryptOptions.None_

    data = response.read()
    if EncodingTypes.BCT_AES_ENCRYPTED in content_type:
        data = decrypt(data, "/chkver2", options)

    if EncodingTypes.BCT_JSON_SERIALIZED in content_type or "json" in content_type:
        return json.loads(data)

    elif EncodingTypes.BCT_MESSAGE_PACK_SERIALIZED in content_type:
        return msgpack.unpackb(data)

    else:
        return data


class EncodingTypes:
    BASE = "application/octet-stream"
    BCT_JSON_SERIALIZED = "jhotuhiahanoatuhinga"
    BCT_MESSAGE_PACK_SERIALIZED = "karerepokai"
    BCT_AES_ENCRYPTED = "fakamunatanga"
    BCT_JSON_AES = f"{BASE}+{BCT_JSON_SERIALIZED}+{BCT_AES_ENCRYPTED}"
    BCT_MESSAGEPACK = f"{BASE}+{BCT_MESSAGE_PACK_SERIALIZED}"
    BCT_MESSAGEPACK_AES = f"{BASE}+{BCT_MESSAGE_PACK_SERIALIZED}+{BCT_AES_ENCRYPTED}"
    BCT_NO_EXTRA_KEY_SALT = "noeks"
