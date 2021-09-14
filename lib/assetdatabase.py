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
        self.f = open(
            self.fp, "rb+", buffering=line_length * buffered_lines
        )

    def end_update_mode(self):
        self.f.close()

    def update_database_entry(self, item: AssetListItem):
        db_item = self.items.get(item.Path)

        if not db_item:
            # in case of multiprocessing, this should be locked
            db_item = AssetDatabaseItem(len(self.items), item.Path, item.Hash)
            self.items[db_item.path] = db_item

        self.f.seek(db_item.line * line_length)
        utf8_bytes = "{:08x}\t{}".format(db_item.hash, db_item.path).encode("utf8")
        self.f.write(
            b"".join([utf8_bytes, b" " * (line_length - len(utf8_bytes) - 1), b"\n"])
        )

    def init_database(self) -> None:
        if os.path.exists(self.fp):
            convert_line = lambda x: (x[1], int(x[0], 16))
            with open(self.fp, "rt", encoding="utf8") as f:
                items = [
                    AssetDatabaseItem(i, *convert_line(line.strip(" ").split("\t", 1)))
                    for i, line in enumerate(f.read().split("\n"))
                    if line
                ]
                self.items = {item.path: item for item in items}
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
