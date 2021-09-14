from collections import namedtuple

Version = namedtuple("Version", "name,api,asset_type,package_id,qooapp_id")

VERSIONS = [
    Version(
        name="global",
        api="app.alcww.gumi.sg",
        asset_type="aetc2",
        package_id="sg.gumi.alchemistww",
        qooapp_id="",
    ),
    Version(
        name="japan",
        api="alchemist.gu3.jp",
        asset_type="win32",
        package_id="jp.co.gu3.alchemist",
        qooapp_id="",
    ),
]
