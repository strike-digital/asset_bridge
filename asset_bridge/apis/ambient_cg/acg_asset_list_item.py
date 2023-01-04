from .acg_asset import ACG_Asset
from ..asset_types import AssetListItem, AssetMetadataItem


class ACG_AssetListItem(AssetListItem):

    def __init__(self, name: str, data: dict):
        self.name = name
        self.idname = name
        self.asset_type = ACG_Asset
        
    def download_preview(self):
        pass
