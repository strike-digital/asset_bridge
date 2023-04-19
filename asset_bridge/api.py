import os
import json
from threading import Thread
from collections import OrderedDict

from .constants import DIRS
from .helpers.math import clamp
from .helpers.process import format_traceback
from .apis.asset_types import AssetList, AssetListItem
from .operators.op_report_message import report_message
"""
The asset lists data structure works like this:

AllAssetLists -> [AssetList, ...] -> [AssetListItem, ...] -> Asset

Each AssetList essentially represents a website source that the assets come from, and
contains information about that site, such as the name, url, and of course a list of
all of the available assets from the site.

Each AssetListItem then contains all of the metadata about an asset
(name, tags, web url etc.), and importantly the quality levels that
are diplayed in the UI.
It is also responsible for downloading the preview of the asset that it represents.
It is meant as a lightweight object only for storing information, rather than doing operations.

Then the Asset differs from the AssetListItem in that it is meant purely for downloading and importing the asset.
An AssetListItem can be converted into an Asset via the .to_asset function.

Thinking about this now, I should maybe have come up with a better naming scheme for it.
"""


class AllAssetLists():
    """Contains a list of all asset Lists, and is a top level structure for accessing their information."""

    asset_lists: OrderedDict[str, AssetList]

    def is_initialized(self, name: str):
        """Check whether an asset list has been initialized with data yet, or if it still needs to be downloaded."""
        return isinstance(self.asset_lists[name], AssetList)

    @property
    def all_initialized(self):
        """Check whether all asset lists have been initialized"""
        for name in self.asset_lists:
            if not self.is_initialized(name):
                return False
        return True

    def initialize_asset_list(self, name, data=None):
        """Takes an asset list and initialises it with new data from the internet"""
        asset_list = self.asset_lists[name]

        # if not data and not check_internet():
        #     report_message(
        #         severity="ERROR",
        #         message="Could not download asset list as there is no internet connection",
        #         main_thread=True,
        #     )
        #     return None

        # Get new data from the internet, from the get_data function
        try:
            asset_list_data = data or asset_list.get_data()
        except Exception as e:
            report_message(
                severity="ERROR",
                message=f"Could not inizialize asset list '{name}' due to error:\n{format_traceback(e)}",
                main_thread=True,
            )
            return None

        # Initialize
        if self.is_initialized(asset_list.name):
            asset_list = asset_list.__class__(asset_list_data)
        else:
            asset_list = asset_list(asset_list_data)
        self.asset_lists[asset_list.name] = asset_list
        for item in asset_list.values():
            item.ab_asset_list = asset_list

        # Write the new cached data
        # This is very slow, so only do it when needed to prevent long register times.
        if not data:
            list_file = DIRS.cache / (asset_list.name + ".json")
            with open(list_file, "w") as f:
                json.dump(asset_list_data, f, indent=2)

        return asset_list

    def initialize_all(self, blocking: bool = True) -> list[Thread]:
        """Initialize all current asset lists
        If blocking is True, wait for initialization to finish,
        otherwise return the threads that are initializing each asset list"""

        # Initialize each one in a separate thread for performance.
        threads = []
        asset_lists = self.asset_lists.copy()
        for asset_list in asset_lists:
            thread = Thread(target=self.initialize_asset_list, args=[asset_list])
            threads.append(thread)
            thread.name = asset_list
            thread.start()

        if blocking:
            for thread in threads:
                thread.join()
        else:
            return threads

    def new_assets_available(self):
        """Return the number of assets that still need to be downloaded"""
        preview_files = os.listdir(DIRS.previews)
        difference = len(self.all_assets) - len(preview_files)
        return clamp(difference, 0, len(self.all_assets))

    def __init__(self):
        self.asset_lists = OrderedDict()

    def __len__(self) -> int:
        return len(self.asset_lists)

    def __getitem__(self, key) -> AssetList:
        return self.asset_lists[key]

    def __setitem__(self, key, value):
        self.asset_lists[key] = value

    def keys(self) -> set[AssetList]:
        return self.asset_lists.keys()

    def values(self) -> set[AssetList]:
        return self.asset_lists.values()

    def items(self) -> set[list[str, AssetList]]:
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
