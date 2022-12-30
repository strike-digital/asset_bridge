from dataclasses import dataclass
from typing import OrderedDict
from abc import ABC, abstractmethod
from bpy.types import ID, UILayout


@dataclass
class AssetMetadataItem():
    """Used to show a row in the asset info table."""

    label: str
    values: str | list[str]

    operator: str = ""
    icon: str = -1

    def draw(self, layout: UILayout):
        row = layout.row(align=True)
        row.label(text=self.label)


class AssetListItem(ABC):
    """A light representation of an asset, only containing info needed for display before being selected"""

    idname: str  # The unique Asset Bridge identifier of this asset
    name: str  # The api name of the asset
    label: str  # The name visible in the UI
    type: str  # HDRI/Texture/Model etc.
    bl_type: ID  # The type of asset to import (World, Object, Material etc.)
    categories: list[str]  # The categories that this asset is in
    authors: list[str]  # The authors of this asset
    catalog_path: str  # The path to the asset in the asset browser

    preview: int = -1
    tags: list[str] = []
    metadata: list[AssetMetadataItem] = []  # Info to be drawn in the metadata table

    @abstractmethod
    def download_preview(self) -> str:
        """Download a preview for this asset.
        Returns an empty string if the download was successful or an error message otherwise"""


class AssetList(ABC):
    """A list of all the assets from an API"""

    name: str
    label: str
    assets: OrderedDict[str, AssetListItem]
    url: str
    description: str

    def __getitem__(self, key) -> AssetListItem:
        return self.assets[key]

    def __setitem__(self, key, value) -> None:
        self.assets[key] = value

    def get(self, key) -> AssetListItem:
        return self.assets.get(key)

    def keys(self) -> set[str]:
        return self.assets.keys()

    def values(self) -> set[AssetListItem]:
        return self.assets.values()

    def items(self) -> set[tuple[str, AssetListItem]]:
        return self.assets.items()

    @staticmethod
    @abstractmethod
    def get_data() -> dict:
        """Return the raw asset list data from the website API as a dict.
        This is then used to initialize the asset list"""

    @abstractmethod
    def __init__(self, data) -> None:
        """Initialize a new asset list from the raw data returned by the website API."""


class Asset(ABC):
    """A functional representation of an asset, used only for downloading or importing assets."""

    category: str
    quality: str
    # task: AssetTask
    list_item: AssetListItem

    @abstractmethod
    def download_asset(self):
        pass

    @abstractmethod
    def import_asset(self):
        pass

    @abstractmethod
    def download_and_import_asset(self):
        pass


# class AssetAPI(ABC):
#     """Represets a website/online api containing assets"""

#     name: str
#     url: str
#     description: str
#     asset_lists: OrderedDict[str, AssetList]

#     @property
#     def all_assets(self):
#         """The assets from all asset lists in this API"""
#         all_assets = ODict()
#         for asset_list in self.asset_lists.values():
#             all_assets.update(asset_list.assets)
#         return all_assets

#     def __getitem__(self, name):
#         return self.all_assets[name]

#     def __setitem__(self, name, value):
#         for asset_list in self.asset_lists.values():
#             if name in asset_list.keys():
#                 asset_list[name] = value
