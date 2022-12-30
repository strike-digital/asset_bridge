from typing import TYPE_CHECKING
from asset_bridge.vendor import requests
from ..asset_types import Asset, AssetListItem as PH_AssetListItem

if TYPE_CHECKING:
    from .ph_asset_list_item import PH_AssetListItem  # noqa F811


class PH_Asset(Asset):

    def __init__(self, asset_list_item: PH_AssetListItem, quality: str = ""):
        self.list_item = asset_list_item
        self.quality = quality
        self.name = asset_list_item.name
        self.type = asset_list_item.type

        self.raw_data = requests.get(f"https://api.polyhaven.com/files/{self.name}").json()

    def download_asset(self):
        return

    def import_asset(self):
        return

    def download_and_import_asset(self):
        return

    def get_quality_data(self) -> dict[str, dict]:
        data = self.raw_data
        if self.type == "hdri":
            return data["hdri"]
        elif self.type in {"texture", "model"}:
            return data["blend"]

    def get_download_size(self, quality_level: str):
        data = self.get_quality_data()[quality_level]
        if self.type == "hdri":
            return data["exr"]["size"]
        else:
            total = 0
            for file in data["blend"]["include"].values():
                total += file["size"]
            if self.type == "model":
                total += data["blend"]["size"]
            return total
