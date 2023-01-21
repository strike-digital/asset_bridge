from collections import OrderedDict
from ..asset_utils import register_asset_list

from .ph_asset_list_item import PH_AssetListItem
from ..asset_types import AssetList
from ...vendor import requests


class PH_AssetList(AssetList):

    name = "poly_haven"
    label = "Poly Haven"
    assets: OrderedDict[str, PH_AssetListItem] = OrderedDict()

    url = "http://polyhaven.com"
    description = """Poly Haven is a curated public asset library for visual effects artists and game designers,
    providing useful high quality 3D assets in an easily obtainable manner.""".replace("\n    ", "")

    @staticmethod
    def get_data() -> dict:
        url = "https://api.polyhaven.com/assets"
        return requests.get(url).json()

    def __init__(self, data: dict):
        self.assets = OrderedDict()
        for name, asset_info in data.items():
            item = PH_AssetListItem(name, asset_info)
            self.assets[item.idname] = item


register_asset_list(PH_AssetList)