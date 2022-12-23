from dataclasses import dataclass
from typing import Callable, Literal, OrderedDict
from ..settings import AssetTask
from bpy.types import UILayout


@dataclass
class AssetMetadataItem():
    """Used to show a row in the asset info table."""

    label: str
    values: list[str]
    operator: str
    icon: str

    def draw(self, layout: UILayout):
        layout.label(text="Info!")


@dataclass
class AssetListItem():
    """A light representation of an asset, only containing info needed for display before being selected"""

    type: str
    preview: int
    quality_levels: list[str]
    categories: list[str]
    tags: list[str]
    metadata: list[AssetMetadataItem]


@dataclass
class AssetList():
    """A list of all the assets from an API"""

    assets: OrderedDict[str, AssetListItem]

    def __getattr__(self, key):
        return self.assets[key]

    def __setattr__(self, key, value):
        self.assets[key] = value


@dataclass
class Asset():
    """A functional representation of an asset, used only for downloading or importing assets."""

    category: str
    quality: str
    task: AssetTask
    list_item: AssetListItem

    def download_asset():
        pass

    def import_asset():
        pass

    def download_and_import_asset():
        pass