from ..asset_utils import download_file, file_name_from_url
from bpy.types import Context
from ..asset_types import Asset, AssetListItem as ACG_AssetListItem

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .acg_asset_list_item import ACG_AssetListItem  # noqa F811


class ACG_Asset(Asset):

    def __init__(self, asset_list_item: ACG_AssetListItem, quality_level: str, link_method: str):
        self.list_item = asset_list_item
        self.name = asset_list_item.name
        self.idname = asset_list_item.idname
        self.type = asset_list_item.type
        self.quality_data = asset_list_item.quality_data
        self.quality_level = quality_level
        self.link_method = link_method

        self.file_type = quality_level.split("-")[-1].lower()

    def get_download_size(self, quality_level: str):
        return self.quality_data[quality_level]["size"]

    def download_asset(self):
        print(self.name, self.type, self.quality_level)
        url = f"https://ambientcg.com/get?file={self.name}_{self.quality_level}.{self.file_type}"
        download_file(url, self.download_dir, file_name_from_url(url))
        pass

    def import_asset(self, context: Context):
        pass

    def download_and_import_asset(self):
        return
