from collections import OrderedDict
from ..asset_utils import register_asset_list

from .acg_asset_list_item import ACG_AssetListItem
from ..asset_types import AssetList
from ...vendor import requests


class ACG_AssetList(AssetList):

    name = "ambient_cg"
    label = "Ambient CG"
    assets: OrderedDict[str, ACG_AssetListItem] = OrderedDict()

    url = "https://ambientcg.com/"
    description = """A massive repository of CC0 assets created by Lennart Demmes""".replace("\n    ", "")

    @staticmethod
    def get_data() -> dict:
        url = "https://api.polyhaven.com/assets"
        return requests.get(url).json()

    def __init__(self, data: dict):
        self.assets = OrderedDict()
        for name, asset_info in data.items():
            # TODO: remove
            return
            self.assets[name] = PH_AssetListItem(name, asset_info)


register_asset_list(ACG_AssetList)