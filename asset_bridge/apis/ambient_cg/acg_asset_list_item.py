import re
from ...helpers.library import human_readable_file_size
from bpy.types import Material, Object, World
from ..asset_utils import HDRI, MATERIAL, MODEL, dimensions_to_string, download_file
from .acg_asset import ACG_Asset
from ..asset_types import AssetListItem, AssetMetadataItem as Metadata


class ACG_AssetListItem(AssetListItem):

    asset_type = ACG_Asset
    authors = ["Lennart Demes"]

    def __init__(self, name: str, data: dict):
        asset_types = {"HDRI": HDRI, "Material": MATERIAL, "3DModel": MODEL}
        bl_types = {"HDRI": World, "Material": Material, "3DModel": Object}
        names = {"HDRI": "HDRIs", "Material": "Materials", "3DModel": "Models"}

        # Necessary data
        self.name = name
        self.idname = name
        data_type = data["dataType"]
        self.type = asset_types[data_type]
        self.bl_type = bl_types[data_type]
        self.tags = data["tags"]
        for tag in data["tags"]:
            if tag not in {"hdri", "3d"}:
                category = tag
                break
        else:
            category = self.tags[-1]
        self.catalog_path = f"{names[data_type]}/{category}"

        # Modify the label
        label = name
        if label.startswith("3D"):
            label = label[2:]
        label = label.replace("HDRI", "")
        label = re.sub("([A-Z])", " \\1", label)[1:]
        label = re.sub("(\\d\\d\\d)", " \\1 ", label)
        self.label = label

        # The quality levels to show in the UI, in the format of an EnumProperty items list
        self.quality_data = data["quality_levels"]
        self.quality_levels = []
        for name, quality_data in data["quality_levels"].items():
            if "PREVIEW" in name:
                continue
            label = name.lower().replace('-', ' ').replace("lq", "Low").replace("sq", "Medium").replace("hq", "High")
            label = f"{label} ({human_readable_file_size(quality_data['size'])})"
            self.quality_levels.append((name, label, f"Download this asset at {label} quality"))
            # self.quality_levels.append((name, name, f"Download this asset at {label} quality"))

        model_levels = ["LQ", "SQ", "HQ"]

        def sort_quality(level: list[str]):
            """Sort the quality levels"""
            name = level[0]
            parts = name.split("-")
            value = 0
            if self.type == HDRI:
                if "TONEMAPPED" in name:
                    value += 100
                qual = parts[0].split("K")[0]
                try:
                    value += int(qual)
                except ValueError as e:
                    print(f"Error sorting quality levels for asset {self.name}: {e}")
            elif self.type == MODEL:
                try:
                    value += model_levels.index(parts[0])
                except ValueError:
                    pass
            return value

        self.quality_levels.sort(key=sort_quality)

        # Setup info for the metadata panel
        self.metadata = [
            Metadata(
                "Link",
                "AmbientCG",
                "wm.url_open",
                operator_kwargs={"url": f"https://ambientcg.com/view?id={data['assetId']}"},
            ),
            Metadata(
                "Author",
                "Lenart Demes",
                "wm.url_open",
                operator_kwargs={"url": "https://www.artstation.com/struffelproductions"},
            ),
            Metadata("type", data["dataType"]),
            Metadata("Downloads", f"{data['downloadCount']:,}"),
            Metadata("Release date", data["releaseDate"].split(" ")[0]),
            Metadata("Creation method", data["creationMethod"]),
            Metadata("tags", data["tags"]),
        ]
        if data["dimensionX"]:
            self.metadata.append(
                Metadata(
                    "Dimensions",
                    [[data["dimensionX"], data["dimensionY"], data["dimensionZ"]]],
                    to_string=dimensions_to_string,
                ))

        self.metadata.append(
            Metadata(
                "Support",
                ["Patreon", "Ko-Fi"],
                "wm.url_open",
                operator_kwargs=[
                    {"url": "https://www.patreon.com/ambientCG"},
                    {"url": "https://ko-fi.com/ambientcg"},
                ],
                label_icon="FUND",
            ),
        )  # yapf: disable

    def download_preview(self):
        url = f"https://cdn3.struffelproductions.com/file/ambientCG/media/sphere/128-PNG/{self.name}_PREVIEW.png"
        download_file(url, self.previews_dir, self.preview_name)
