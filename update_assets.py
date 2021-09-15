import json
import os
from multiprocessing import pool, cpu_count
from typing import List, Tuple
from PIL import Image
import msgpack
from lib.versions import VERSIONS, Version
from lib.paths import ASSETS, RES
from lib.version import load_version_consts, update_version_consts
from lib.api import req_asset, req_chkver2
from lib import encryption_helper
from lib.assetlist import AssetList, AssetListItem
from lib.assetdatabase import AssetDatabase
from lib.asset_extractor import extract_asset


def main():
    for version in VERSIONS:
        try:
            update_version(version)
        except Exception as e:
            print(e)
        print("\n\n")


def update_version(version: Version) -> None:
    extraction_path = os.path.join(ASSETS, version.name)

    print("Updating", version.name.title())
    print("===================")

    # load local settings
    print("~~ version constants ~~")
    network_ver, shared_key = load_version_consts(version)
    print("network version:", network_ver)
    print("shared key:", shared_key)
    encryption_helper.a_shared_key = shared_key
    print()

    # fetch the current environment
    ver_res = req_chkver2(version.api, network_ver)
    ver_status = ver_res["stat"]
    if ver_status == 1100:
        print("version constants are outdated")
        network_ver, shared_key = update_version_consts(version)
        print("network version:", network_ver)
        print("shared key:", shared_key)
        ver_res = req_chkver2(version.api, network_ver)
        print()

    elif ver_res.get("stat") != 0:
        print("Unhandled error during the version request")
        raise NotImplementedError(f'Status: {ver_res["status"]}, {ver_res["stat_msg"]}')

    print("~~ environment ~~")
    environment = ver_res["body"]["environments"]["alchemist"]
    print("asset host:", environment["host_dl"])
    print("asset version:", environment["assets"])
    print("master digest:", environment["master_digest"])
    print("quest digest:", environment["quest_digest"])
    print()

    # fetch the assetlist
    print("~~ asset check ~~")

    print("downloading latest assetlist")
    asset_url = (
        f"{environment['host_dl']}/assets/{environment['assets']}/{version.asset_type}"
    )
    raw_assetlist = req_asset(asset_url, "ASSETLIST")
    assetlist = AssetList(raw_assetlist)

    # get local assetlist/database
    print("reading local asset database")
    assetdatabase_path = os.path.join(RES, f"asset_database_{version.name}.txt")
    assetdb = AssetDatabase(assetdatabase_path)

    # get new assets
    print("looking for new and changed assets")
    new_assets, updated_assets = assetdb.check_assets(assetlist)
    print("new assets:", len(new_assets))
    print("updated assets:", len(updated_assets))
    print()

    print("~~ asset download and extraction ~~")
    assetdb.start_update_mode()
    if new_assets:
        print("- new assets -")
        update_assets(extraction_path, asset_url, new_assets, assetdb)
        # for i, item in enumerate(new_assets):
        #     print(f"{i+1}/{len(new_assets)} - {item.Path}")
        #     asset_data = req_asset(asset_url, f"{item.ID:08x}")
        #     extract_asset(extraction_path, asset_data, item)
        #     assetdb.update_database_entry(item)

    if updated_assets:
        print("- updated assets -")
        update_assets(extraction_path, asset_url, updated_assets, assetdb)
        # for i, item in enumerate(updated_assets):
        #     print(f"{i+1}/{len(new_assets)} - {item.Path}")
        #     asset_data = req_asset(asset_url, f"{item.ID:08x}")
        #     extract_asset(extraction_path, asset_data, item)
        #     assetdb.update_database_entry(item)
    assetdb.end_update_mode

    print("~~ file fixes ~~")
    print("check that MasterParam,QuestParam, and QuestDropParam are json")
    data_path = os.path.join(extraction_path, "Data")
    check_param(data_path, "MasterParam", environment["master_digest"])
    check_param(data_path, "QuestParam", environment["quest_digest"])
    check_param(data_path, "QuestDropParam", environment["quest_digest"])

    print("crop concept cards")
    crop_conceptcards(extraction_path)

    # TODO print("convert music")
    print()

    print("~~ done ~~")


def update_assets(
    extraction_path: str,
    asset_url: str,
    items: List[AssetListItem],
    assetdb: AssetDatabase,
) -> None:
    ppool = pool.ThreadPool(cpu_count())
    for i, result in enumerate(
        ppool.imap_unordered(
            update_asset, ((extraction_path, asset_url, item) for item in items)
        )
    ):
        print(f"{i+1}/{len(items)} - {result.Path}")
        assetdb.update_database_entry(result)


def update_asset(args: Tuple[str, str, AssetListItem]) -> AssetListItem:
    extraction_path, asset_url, item = args
    asset_data = req_asset(asset_url, f"{item.ID:08x}")
    try:
        extract_asset(extraction_path, asset_data, item)
    except Exception as e:
        print(item.Path, e)
    return item


def check_param(data_path: str, name: str, digest: str) -> None:
    enc_data = None
    sfp = os.path.join(data_path, f"{name}Serialized.txt")
    dfp = os.path.join(data_path, f"{name}.json")
    if os.path.exists(sfp):
        with open(sfp, "rb") as f:
            enc_data = f.read()
            dec_data = encryption_helper.decrypt(
                enc_data, digest, encryption_helper.DecryptOptions.IsFile
            )
            if dec_data[:1] == b"{" and dec_data[-1:] == b"}":
                data = json.loads(dec_data)
            else:
                data = msgpack.unpackb(dec_data)
    else:
        with open(dfp, "rt", encoding="utf8") as f:
            data = json.load(f)

    with open(dfp, "wt", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def crop_conceptcards(extraction_path: str) -> None:
    concept_path = os.path.join(extraction_path, "ConceptCard")
    for card in os.listdir(concept_path):
        f = os.path.join(concept_path, card)
        try:
            img = Image.open(f)
        except:
            print(f"Can't open {card} as image.")
            continue
        if (1024, 612) != img.size:
            print("cropping", card)
            img = img.crop((0, 0, 1024, 612))
            img.save(f)


if __name__ == "__main__":
    main()
