from collections import OrderedDict
from .apis.asset_types import AssetAPI, AssetListItem


class APIs():
    """Contains a list of all APIs, and is a top level structure for accessing their information."""

    apis: OrderedDict[str, AssetAPI]

    def __init__(self):
        self.apis = OrderedDict()

    def __len__(self):
        return len(self.apis)

    def __getitem__(self, key):
        return self.apis[key]

    def __setitem__(self, key, value):
        self.apis[key] = value

    def keys(self):
        return self.apis.keys()

    def values(self):
        return self.apis.values()

    def items(self):
        return self.apis.items()

    @property
    def all_assets(self) -> OrderedDict[str, AssetListItem]:
        all_assets = OrderedDict()
        for api in self.apis.values():
            all_assets.update(api.all_assets)
        return all_assets


apis: APIs = APIs()


def get_apis() -> APIs:
    return apis
