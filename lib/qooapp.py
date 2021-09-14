from urllib.request import Request, urlopen
from urllib.parse import urlencode


def download_QooApp_apk(package_id):
    query = urlencode(
        {
            "supported_abis": "x86,armeabi-v7a,armeabi",
            "device": "beyond1q",
            "base_apk_version": "0",
            "locale": "en",
            "opengl": "196609",
            "rooted": "true",
            "screen": "900,1600",
            "userId": "58009610",
            "device_model": "SM-G973N",
            "sdk_version": "22",
            "base_apk_md5": "null",
            "user_id": "58009610",
            "version_code": "317",
            "version_name": "8.1.7",
            "os": "android+5.1.1",
            "adid": "64d6639f-55fe-4a86-86fa-a5ea31b2adc7",
            "type": "app",
            "uuid": "7e86a27e-db1c-4072-a5cc-e4b9b08e0672",
            "device_id": "80e65e35094bedcc",
            "package_id": "com.qooapp.qoohelper",
            "otome": "0",
            "token": "049b1432e342d571a01235ec1d6a91f61fc1db2e",
            "android_id": "80e65e35094bedcc",
            "sa_distinct_id": "80e65e35094bedcc",
            "patch_code": "48",
            "density": "320",
            "system_locale": "en_DE",
        }
    )
    res = urlopen(Request(
        url=f"https://api.qoo-app.com/v6/apps/{package_id}/download?{query}",
        headers={
            "accept-encoding": "gzip",
            "user-agent": "QooApp 8.1.7",
            "device-id": "80e65e35094bedcc",
        },
        method="GET"
    ))
    return res.read()
