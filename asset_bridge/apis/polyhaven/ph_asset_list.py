from collections import OrderedDict
from ..asset_utils import AssetList


class PH_AssetList(AssetList):

    def get_data(self):
        print("Data!")
        return {}

    def __init__(self, data):
        self.assets = OrderedDict()
        pass