from bpy.types import Context
from ..asset_types import Asset, AssetListItem as ACG_AssetListItem
from ...vendor import requests

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .acg_asset_list_item import ACG_AssetListItem  # noqa F811


class ACG_Asset(Asset):

    def __init__(self, asset_list_item: ACG_AssetListItem):
        self.list_item = asset_list_item
        self.name = asset_list_item.name
        self.idname = asset_list_item.idname
        self.type = asset_list_item.type

        # example: https://api.polyhaven.com/files/carrot_cake
        # TODO: switch to ambient CG
        self.raw_data = requests.get(f"https://api.polyhaven.com/files/{self.name}").json()

    def get_download_size(self, quality_level: str):
        pass

    def download_asset(self):
        pass

    def import_asset(self, context: Context):
        pass

    def download_and_import_asset(self):
        return
