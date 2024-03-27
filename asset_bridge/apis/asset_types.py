from __future__ import annotations

import os
from abc import ABC, abstractmethod
import sys
from typing import Type, Literal, Callable, OrderedDict
from pathlib import Path
from itertools import zip_longest
from dataclasses import field, dataclass

from bpy.types import ID, Context, UILayout
from ..previews import get_icon

from ..constants import DIRS


@dataclass
class AssetMetadataItem():
    """Used to show a row in the asset info table."""

    label: str
    values: str | list[str]

    operator: str = ""
    operator_kwargs: dict | list[dict] = field(default_factory=dict)
    icons: str | list[str] = "NONE"
    to_string: Callable = None  # A function that takes a value and returns a formatted string
    label_icon: str = "NONE"

    def draw(self, layout: UILayout, context: Context):
        row = layout.row(align=True)
        operator = self.operator

        split = row.split(align=True)
        left = split.box().column(align=True)
        label = self.label if self.label.endswith(":") else self.label + ":"
        left.label(text=label, icon=self.label_icon)
        left.scale_y = .75

        values = self.values
        if isinstance(values, str):
            values = [values]

        icons = self.icons
        if isinstance(icons, str):
            icons = [icons] * len(values)

        operator_kwargs = self.operator_kwargs
        if isinstance(operator_kwargs, dict):
            operator_kwargs = [operator_kwargs]

        right_row = split.box().row(align=True)
        right = right_row.column(align=True)
        right.scale_y = left.scale_y
        for icon, kwargs, val in zip_longest(icons, operator_kwargs, values):
            right.alignment = "LEFT"
            label = self.to_string(val) if self.to_string else val
            right.label(text=f" {label}", icon=icon or "NONE")
            """This is some magic that places the operator button on top of the label,
            which allows the text to be left aligned rather than in the center.
            It works by creating a dummy row above the operator, and then giving it a negative scale,
            which pushes the operator up to be directly over the text.
            If you want to see what it's doing, set emboss to True and change the sub.scale_y parameter.
            It is also entirely overkill"""
            if operator:
                subcol = right.column(align=True)
                sub = subcol.column(align=True)
                sub.scale_y = -1
                sub.prop(context.scene.render, "resolution_x")  # A random property
                subrow = subcol.row(align=True)
                op = subrow.operator(operator, text="", emboss=True)
                for name, value in kwargs.items():
                    setattr(op, name, value)

            if val != list(values)[0]:
                left.label(text="")


class AssetListItem(ABC):
    """A light representation of an asset, only containing info needed for display before being selected"""

    # Attributes starting with ab_ are reserved and used by the addon

    ab_asset_type: Type[Asset]  # The api asset class
    ab_asset_list: AssetList  # The asset list that this list item is contained within

    ab_is_valid: bool = True  # Don't include this asset
    ab_prefix: str  # Used as a prefix for the assets idname, to ensure that all asset names are unique
    ab_idname: str  # The unique Asset Bridge identifier of this asset
    ab_name: str  # The api name of the asset
    ab_label: str  # The name visible in the UI
    ab_type: str  # HDRI/Texture/Model etc.
    ab_bl_type: ID  # The type of asset to import (World, Object, Material etc.)
    ab_categories: list[str]  # The categories that this asset is in
    ab_authors: list[str]  # The authors of this asset
    ab_catalog_path: str  # The path to the asset in the asset browser

    ab_material_size: float = 1.0  # The real world size of a material in meters

    # The different levels of quality in the format of blender enum property items
    ab_quality_levels: list[tuple[str, str, str]]

    ab_tags: list[str] = []
    ab_metadata: list[AssetMetadataItem] = []  # Info to be drawn in the metadata table

    @property
    def ab_idname(self):
        return f"{self.ab_prefix}_{self.ab_name}"

    @property
    def downloads_dir(self):
        """The directory where all of the asset files will be downloaded to.
        IMPORTANT: This is for *All* quality levels, use the Asset class for a specific level, or do it manually"""
        return DIRS.assets / self.ab_idname

    @property
    def preview_name(self):
        return self.ab_idname + ".png"

    @property
    def previews_dir(self):
        return DIRS.previews

    @property
    def preview_file(self):
        return self.previews_dir / self.preview_name

    @property
    def progress_file(self):
        return DIRS.dummy_assets / f"{self.ab_name}"

    def get_quality_dir(self, quality_level: str):
        return self.downloads_dir / quality_level

    def poll(self):
        """Whether this asset can be imported currently.
        Return an empty string if it can, and an error to show if it can't."""
        return ""

    @abstractmethod
    def download_preview(self) -> str:
        """Download a preview for this asset.
        Returns an empty string if the download was successful or an error message otherwise"""

    def get_high_res_urls(self) -> list[str]:
        """return a list of high resolution preview image urls for this asset"""

    def to_asset(
        self,
        quality_level: str,
        link_method: Literal["LINK", "APPEND", "APPEND_REUSE"],
    ) -> Asset:
        """Return an Asset type for downloading and importing of this asset"""
        asset = self.ab_asset_type(self, quality_level, link_method)
        # asset.quality = quality_level
        # asset.link_method = link_method
        return asset

    def is_downloaded(self, quality_level) -> bool:
        """Return whether this asset has been downloaded at a certain quality level"""
        quality_dir = self.downloads_dir / quality_level
        if not quality_dir.exists():
            return False
        if not os.listdir(quality_dir):
            return False
        return True

    def __str__(self):
        return f"<{self.ab_asset_list.name}_list_item: {self.ab_idname}>"


class AssetList(ABC):
    """A list of all the assets from an API"""

    name: str
    label: str
    assets: OrderedDict[str, AssetListItem]
    url: str
    support_url: str
    description: str
    categories: list[str]

    @property
    def icon_path(self) -> Path:
        """The path to the icon for this asset list.
        By default this is 'api_folder / {list_prefix}_logo.png', but it can be overriden if needed"""
        file = sys.modules[self.__class__.__module__].__file__  # Get the api folder
        return Path(file).parent / f"{list(self.assets.values())[0].ab_prefix}_logo.png"

    @property
    def icon(self):
        """Get the icon for this asset library.
        Requires the icon_path to be set."""
        return get_icon(self.icon_path.stem)

    @classmethod
    @property
    def data_cache_file(self) -> Path:
        return DIRS.cache / (self.name + ".json")

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

    def __str__(self) -> str:
        return f"<asset_list: {self.name}>"


class Asset(ABC):
    """A functional representation of an asset, used only for downloading or importing assets."""

    list_item: AssetListItem
    quality_level: str
    link_method: Literal["LINK", "APPEND", "APPEND_REUSE"]

    @property
    def download_dir(self) -> Path:
        """The directory that the asset files will be downloaded to"""
        return self.list_item.downloads_dir / self.quality_level

    @property
    def import_name(self) -> str:
        """The name of the asset once it has been imported as a data block"""
        return f"{self.list_item.ab_idname}_{self.quality_level}"

    @property
    def is_downloaded(self) -> bool:
        """Whether this asset has been downloaded"""
        return self.list_item.is_downloaded(self.quality_level)

    @abstractmethod
    def __init__(
        self,
        asset_list_item: AssetListItem,
        quality_level: str,
        link_method: Literal["LINK", "APPEND", "APPEND_REUSE"],
    ):
        pass

    @abstractmethod
    def get_download_size(self):
        """Return the number of bytes that need to be downloaded"""

    @abstractmethod
    def download_asset(self):
        pass

    @abstractmethod
    def import_asset(self, context: Context):
        pass

    def get_files(self) -> list[Path]:
        "Get a list of downloaded files"
        files = []
        for (dirpath, dirnames, filenames) in os.walk(self.download_dir):
            files += [Path(dirpath) / file for file in filenames]
        return files

    def __str__(self):
        return f"<{self.ab_asset_list.name}_asset: {self.list_item.ab_idname}>"
