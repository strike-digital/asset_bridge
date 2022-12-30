from dataclasses import dataclass, field
from itertools import zip_longest
import os
from typing import Callable, OrderedDict
from abc import ABC, abstractmethod

from ..constants import DIRS
from bpy.types import ID, Context, UILayout


@dataclass
class AssetMetadataItem():
    """Used to show a row in the asset info table."""

    label: str
    values: str | list[str]

    operator: str = ""
    operator_kwargs: dict | list[dict] = field(default_factory=dict)
    icon: str = "NONE"
    to_string: Callable = None  # A function that takes a value and returns a formatted string

    def draw(self, layout: UILayout, context: Context):
        row = layout.row(align=True)
        operator = self.operator

        split = row.split(align=True)
        left = split.box().column(align=True)
        label = self.label if self.label.endswith(":") else self.label + ":"
        left.label(text=label)
        left.scale_y = .75

        values = self.values
        if isinstance(values, str):
            values = [values]

        operator_kwargs = self.operator_kwargs
        if isinstance(operator_kwargs, dict):
            operator_kwargs = [operator_kwargs]

        right_row = split.box().row(align=True)
        right = right_row.column(align=True)
        right.scale_y = left.scale_y
        for kwargs, val in zip_longest(operator_kwargs, values):
            right.alignment = "LEFT"
            label = self.to_string(val) if self.to_string else val
            right.label(text=f" {label}", icon=self.icon)
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

    idname: str  # The unique Asset Bridge identifier of this asset
    name: str  # The api name of the asset
    label: str  # The name visible in the UI
    type: str  # HDRI/Texture/Model etc.
    bl_type: ID  # The type of asset to import (World, Object, Material etc.)
    categories: list[str]  # The categories that this asset is in
    authors: list[str]  # The authors of this asset
    catalog_path: str  # The path to the asset in the asset browser

    # The different levels of quality in the format of blender enum property items
    quality_levels: list[tuple[str, str, str]]

    preview: int = -1
    tags: list[str] = []
    metadata: list[AssetMetadataItem] = []  # Info to be drawn in the metadata table

    @abstractmethod
    def download_preview(self) -> str:
        """Download a preview for this asset.
        Returns an empty string if the download was successful or an error message otherwise"""

    def is_downloaded(self, quality_level) -> bool:
        """Return whether this asset has been downloaded at a certain quality level"""
        assets_dir = DIRS.assets
        quality_dir = assets_dir / self.idname / quality_level
        if not quality_dir.exists():
            return False
        if not os.listdir(quality_dir):
            return False
        return True


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

    quality: str = ""
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
