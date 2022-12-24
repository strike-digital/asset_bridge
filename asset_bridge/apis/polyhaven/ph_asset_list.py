from collections import OrderedDict
from ..asset_types import AssetList


class PH_AssetList(AssetList):

    name = "PolyHavenAssetList"

    @staticmethod
    def get_data():
        print("Data!")
        return {}

    def __init__(self, data):
        self.assets = OrderedDict()
        pass