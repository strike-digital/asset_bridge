from ...helpers.library import human_readable_file_size
from .ph_asset import PH_Asset
from bpy.types import Material, Object, World
from ...constants import DIRS

from ..asset_utils import download_file
from ..asset_types import AssetListItem, AssetMetadataItem


class PH_AssetListItem(AssetListItem):

    def __init__(self, name: str, data: dict):
        self.asset: PH_Asset = None

        asset_types = ["hdri", "texture", "model"]
        bl_types = [World, Material, Object]
        self.name = name
        self.label = data["name"]
        self.idname = name
        self.type = asset_types[data["type"]]
        self.bl_type = bl_types[data["type"]]
        self.authors = list(data["authors"].keys()) or [""]

        self.categories = data["categories"]
        names = ["Hdris", "Textures", "Models"]
        self.catalog_path = f"{names[data['type']]}/{self.categories[0]}"

        self.tags = data["tags"] + data["categories"]
        self.page_url = f"https://polyhaven.com/a/{name}"

        # TODO: Add more and make them context sensitive
        self.metadata = [
            AssetMetadataItem("Link", self.page_url, "wm.url_opn"),
            AssetMetadataItem("Downloads", f"{data['download_count']:,}"),
            AssetMetadataItem("Tags", data["tags"])
        ]

        # TODO: Maybe load the preview here
        pass

    @property
    def quality_levels(self):
        """The quality levels of Poly haven assets aren't accessible from the normal asset list,
        So here we load the full asset and cache it, use its data to get the quality levels."""
        if not self.asset:
            self.asset = PH_Asset(self)
        items = []
        quality_data = list(self.asset.get_quality_data())
        quality_data.sort()
        for name in quality_data:
            size = human_readable_file_size(self.asset.get_download_size(name)).replace(" ", "")
            label = f"{name} ({size})"
            items.append((name, label, f"Load asset at {name} resolution"))
        return items

    def download_preview(self):
        size = 128
        url = f"https://cdn.polyhaven.com/asset_img/thumbs/{self.name}.png?width={size}&height={size}"
        download_file(url, DIRS.previews, f"{self.idname}.png")