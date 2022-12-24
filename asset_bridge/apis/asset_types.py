from dataclasses import dataclass
from typing import Dict, OrderedDict
from abc import ABC, abstractmethod
from bpy.types import UILayout


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

    type: str
    label: str
    categories: list[str]

    preview: int = -1
    tags: list[str] = []
    metadata: list[AssetMetadataItem] = []


class AssetList(ABC):
    """A list of all the assets from an API"""

    assets: OrderedDict[str, AssetListItem]

    def __getitem__(self, key):
        return self.assets[key]

    def __setitem__(self, key, value):
        self.assets[key] = value

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


class AssetAPI(ABC):

    name: str
    url: str
    description: str
    asset_lists: Dict[str, AssetList]