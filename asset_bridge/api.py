from collections import OrderedDict
from .apis.asset_types import AssetList, AssetListItem


class AllAssetLists():
    """Contains a list of all asset Lists, and is a top level structure for accessing their information."""

    asset_lists: OrderedDict[str, AssetList]

    def __init__(self):
        self.asset_lists = OrderedDict()

    def __len__(self):
        return len(self.asset_lists)

    def __getitem__(self, key):
        return self.asset_lists[key]

    def __setitem__(self, key, value):
        self.asset_lists[key] = value

    def keys(self):
        return self.asset_lists.keys()

    def values(self):
        return self.asset_lists.values()

    def items(self):
        return self.asset_lists.items()

    @property
    def all_assets(self) -> OrderedDict[str, AssetListItem]:
        all_assets = OrderedDict()
        for asset_list in self.asset_lists.values():
            all_assets.update(asset_list.assets)
        return all_assets


asset_lists: AllAssetLists = AllAssetLists()


def get_asset_lists() -> AllAssetLists:
    return asset_lists
