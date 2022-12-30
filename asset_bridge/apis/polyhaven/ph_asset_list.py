from collections import OrderedDict
from ..asset_utils import register_asset_list

from asset_bridge.apis.polyhaven.ph_asset_list_item import PH_AssetListItem
from ..asset_types import AssetList
from ...vendor import requests


class PH_AssetList(AssetList):

    name = "poly_haven"
    label = "Poly Haven"
    assets = OrderedDict()

    url = "http://polyhaven.com"
    description = """Poly Haven is a curated public asset library for visual effects artists and game designers,
    providing useful high quality 3D assets in an easily obtainable manner.""".replace("\n    ", "")

    @staticmethod
    def get_data() -> dict:
        url = "https://api.polyhaven.com/assets"
        print("Data!")
        return requests.get(url).json()

    def __init__(self, data: dict):
        self.assets = OrderedDict()
        for name, asset_info in data.items():
            self.assets[name] = PH_AssetListItem(name, asset_info)


register_asset_list(PH_AssetList)