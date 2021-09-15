import os
from typing import Any, Dict, List
from collections import namedtuple
from .assetlist import AssetList, AssetListItem, AssetBundleFlags

AssetDatabaseItem = namedtuple("AssetDatabaseItem", "line,path,hash")

line_length = 256
buffered_lines = 32


class AssetDatabase:
    f: Any
    fp: str
    items: Dict[str, AssetDatabaseItem]

    def __init__(self, fp: str) -> None:
        self.f = None
        self.fp = fp
        self.items = {}
        self.init_database()

    def start_update_mode(self):
        if not os.path.exists(self.fp):
            open(self.fp, "wt", encoding="utf8").close()
        self.f = open(self.fp, "rb+", buffering=line_length * buffered_lines)

    def end_update_mode(self):
        # self.f.flush()
        self.f.close()

    def update_database_entry(self, item: AssetListItem):
        db_item = self.items.get(item.Path)

        if not db_item:
            # in case of multiprocessing, this should be locked
            db_item = AssetDatabaseItem(len(self.items), item.Path, item.Hash)
            self.items[db_item.path] = db_item

        self.f.seek(db_item.line * line_length)
        utf8_bytes = "{:08x}\t{}".format(item.Hash, item.Path).encode("utf8")
        self.f.write(
            b"".join([utf8_bytes, b" " * (line_length - len(utf8_bytes) - 1), b"\n"])
        )

    def init_database(self) -> None:
        if os.path.exists(self.fp):
            lines = []
            with open(self.fp, "rt", encoding="utf8") as f:
                lines = [x.strip(" ").split("\t") for x in f.read().split("\n") if x]
            raw_items = {path: int(hash, 16) for hash, path in lines}
            if len(raw_items) != len(lines):
                print("Duplicates found within the local asset database")
                print("purging them now")
                raw_line_list = []
                for path, hash in raw_items.items():
                    utf8_bytes = "{:08x}\t{}".format(hash, path).encode("utf8")
                    raw_line_list.append(
                        b"".join(
                            [
                                utf8_bytes,
                                b" " * (line_length - len(utf8_bytes) - 1),
                                b"\n",
                            ]
                        )
                    )
                with open(self.fp, "wb") as f:
                    f.write(b"".join(raw_line_list))

            self.items = {
                path: AssetDatabaseItem(i, path, hash)
                for i, (path, hash) in enumerate(raw_items.items())
            }
        else:
            self.items = {}

    def check_assets(self, assetlist: AssetList):
        new_items: List[AssetListItem] = []
        updated_items: List[AssetListItem] = []

        for list_item in assetlist.mItems:
            if AssetBundleFlags.IsCombined & list_item.Flags or not list_item.Path:
                continue
            db_item = self.items.get(list_item.Path, None)
            if not db_item:
                new_items.append(list_item)
            elif db_item.hash != list_item.Hash:
                updated_items.append(list_item)

        return new_items, updated_items
