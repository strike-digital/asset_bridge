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
        self.downloads_path = self.list_item.downloads_path / quality

        # example: https://api.polyhaven.com/files/carrot_cake
        self.raw_data = requests.get(f"https://api.polyhaven.com/files/{self.name}").json()

    def get_quality_data(self) -> dict[str, dict]:
        data = self.raw_data
        if self.type == "hdri":
            return data["hdri"]
        elif self.type in {"texture", "model"}:
            return data["blend"]

    def get_files_to_download(self, quality_level: str):
        data = self.get_quality_data()[quality_level]
        if self.type == "hdri":
            return [data["exr"]]
        else:
            files = []
            files = list(data["blend"]["include"].values())
            if self.type == "model":
                files.append(data["blend"])
            return files

    def get_download_size(self, quality_level: str):
        return sum([f["size"] for f in self.get_files_to_download(quality_level)])

    def download_asset(self):
        if not self.quality:
            raise ValueError(f"Cannot download {self.name} without providing a quality level")

        # if self.type == "model":

        files = self.get_files_to_download(self.quality)
        for file in files:
            print(file["url"])
        return

    def import_asset(self):
        return

    def download_and_import_asset(self):
        return
