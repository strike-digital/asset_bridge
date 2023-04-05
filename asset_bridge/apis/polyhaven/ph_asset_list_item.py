from datetime import datetime
from threading import Thread
from bpy.types import Material, Object, World

from .ph_asset import PH_Asset
from ..asset_utils import HDRI, MATERIAL, MODEL, dimensions_to_string, download_file
from ..asset_types import AssetListItem, AssetMetadataItem
from ...helpers.main_thread import force_ui_update
from ...helpers.library import human_readable_file_size
from ...constants import DIRS


class PH_AssetListItem(AssetListItem):

    acronym = "ph"
    asset_type = PH_Asset

    def __init__(self, name: str, data: dict):
        self.asset: PH_Asset = None

        asset_types = [HDRI, MATERIAL, MODEL]
        bl_types = [World, Material, Object]
        self.name = name
        self.label = data["name"]
        self.type = asset_types[data["type"]]
        self.bl_type = bl_types[data["type"]]
        self.authors = list(data["authors"].keys()) or [""]

        self.categories = data["categories"]
        # names = ["HDRIs", "Materials", "Models"]
        # self.catalog_path = f"{names[data['type']]}/{self.categories[0]}"

        self.tags = data["tags"] + data["categories"]
        self.page_url = f"https://polyhaven.com/a/{name}"

        self.loading_asset = False

        # Add metadata items
        self.metadata = [
            AssetMetadataItem(
                "Link",
                "Poly Haven",
                "wm.url_open",
                operator_kwargs={"url": self.page_url},
            ),
            AssetMetadataItem(
                f"Author{'s' if len(data['authors']) > 1 else ''}",
                data["authors"],
                operator="asset_bridge.open_ph_author_website",
                operator_kwargs=[{"author_name": name} for name in data["authors"]],
            ),
            AssetMetadataItem(
                "Downloads",
                f"{data['download_count']:,}",
            ),
        ]  # yapf: disable

        if "dimensions" in data:
            # This needs the context to work so pass it as an argument
            self.metadata.append(AssetMetadataItem(
                "Dimensions",
                [data["dimensions"]],
                to_string=dimensions_to_string,
            ))

        if "evs" in data:
            self.metadata.append(AssetMetadataItem("EVs", str(data["evs"])))

        if "whitebalance" in data:
            self.metadata.append(AssetMetadataItem("Whitebalance", f"{str(data['whitebalance'])}K"))

        self.metadata.append(
            AssetMetadataItem(
                "Date published",
                datetime.fromtimestamp(data["date_published"]).strftime(format="%d/%m/%Y"),
            ))

        if "date_taken" in data:
            self.metadata.append(
                AssetMetadataItem(
                    "Date taken",
                    datetime.fromtimestamp(data["date_taken"]).strftime(format="%d/%m/%Y"),
                ))

        self.metadata.append(AssetMetadataItem(
            "Tags",
            data["tags"],
        ))
        self.metadata.append(
            AssetMetadataItem(
                "Support",
                "Patreon",
                "wm.url_open",
                operator_kwargs={"url": "https://www.patreon.com/polyhaven/overview"},
                label_icon="FUND",
            ))

    @property
    def quality_levels(self):
        """The quality levels of Poly haven assets aren't accessible from the normal asset list,
        So here we load the full asset and cache it, use its data to get the quality levels."""
        if not self.asset:

            def load_asset():
                asset = PH_Asset(self)
                self.asset = asset
                self.loading_asset = False
                force_ui_update(area_types={"FILE_BROWSER"}, region_types={"TOOLS"})

            if not self.loading_asset:
                thread = Thread(target=load_asset)
                thread.start()
                self.loading_asset = True
            return [("1k", "1k (00MB)", "1k")]

        items = []
        quality_data = list(self.asset.get_quality_data())
        quality_data.sort(key=lambda name: int(name.split("k")[0]))
        for name in quality_data:
            self.asset.quality_level = name
            size = human_readable_file_size(self.asset.get_download_size()).replace(" ", "")
            label = f"{name} ({size})"
            items.append((name, label, f"Load asset at {name} resolution"))
        return items

    def download_preview(self, size=128):
        url = f"https://cdn.polyhaven.com/asset_img/thumbs/{self.name}.png?width={size}&height={size}"
        download_file(url, DIRS.previews, f"{self.idname}.png")
