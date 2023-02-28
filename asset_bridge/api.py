import os
import json
from threading import Thread
from collections import OrderedDict

from .constants import DIRS
from .helpers.math import clamp
from .helpers.general import check_internet
from .helpers.process import format_traceback
from .apis.asset_types import AssetList, AssetListItem
from .operators.op_report_message import report_message


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

        if not data and not check_internet():
            report_message(
                severity="ERROR",
                message="Could not download asset list as there is no internet connection",
                main_thread=True,
            )
            return None

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
            item.asset_list = asset_list

        # Ensure that there are no duplicate names in other apis, so that all assets can be accessed by name
        # for name, asset in asset_list.assets.items():
        #     asset.idname = f"{asset_list.acronym}_{asset.idname}"

        # for name, other_list in self.asset_lists.items():
        #     if name == asset_list.name:
        #         continue

        #     if duplicates := other_list.assets.keys() & asset_list.assets.keys():
        #         for duplicate in duplicates:
        #             asset = asset_list[duplicate]
        #             del asset_list[duplicate]
        #             asset_list[f"{duplicate}_1"] = asset
        #             asset.idname = f"{duplicate}_1"

        # Write the new cached data
        # This is very slow, so only do it when needed to prevent long register times.
        if not data:
            list_file = DIRS.asset_lists / (asset_list.name + ".json")
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
