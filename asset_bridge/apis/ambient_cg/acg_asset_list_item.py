import inspect
import re
from traceback import format_exc

from bpy.types import Material, Object, World

from ...helpers.library import human_readable_file_size
from ..asset_types import AssetListItem
from ..asset_types import AssetMetadataItem as Metadata
from ..asset_utils import HDRI, MATERIAL, MODEL, dimensions_to_string, download_file
from .acg_asset import ACG_Asset


class ACG_AssetListItem(AssetListItem):
    ab_asset_type = ACG_Asset
    ab_prefix = "acg"
    ab_authors = ["Lennart Demes"]

    def __init__(self, name: str, data: dict):
        asset_types = {"HDRI": HDRI, "Material": MATERIAL, "3DModel": MODEL}
        bl_types = {"HDRI": World, "Material": Material, "3DModel": Object}

        # Necessary data
        self.ab_name = name
        data_type = data["dataType"]
        self.ab_type = asset_types[data_type]
        self.ab_bl_type = bl_types[data_type]
        self.ab_tags = data["tags"]
        self.ab_categories = [t for t in self.ab_tags if t not in {"hdri", "3d"} and not re.match("\d+", t)]
        # self.catalog_path = f"{names[data_type]}/{category}"

        # Modify the label
        label = name
        if label.startswith("3D"):
            label = label[2:]
        label = label.replace("HDRI", "")
        label = re.sub("([A-Z])", " \\1", label)[1:]
        label = re.sub("(\\d\\d\\d)", " \\1 ", label)
        self.ab_label = label

        # The quality levels to show in the UI, in the format of an EnumProperty items list
        try:
            self.quality_data = data["quality_levels"]
        except KeyError:
            # If no quality levels, asset is not valid
            self.ab_is_valid = False
            return

        self.ab_quality_levels = []
        for name, quality_data in data["quality_levels"].items():
            if "PREVIEW" in name:
                continue
            label = name.lower().replace("-", " ").replace("lq", "Low").replace("sq", "Medium").replace("hq", "High")
            label = f"{label} ({human_readable_file_size(quality_data['size'])})"
            self.ab_quality_levels.append((name, label, f"Download this asset at {label} quality"))
            # self.quality_levels.append((name, name, f"Download this asset at {label} quality"))

        model_levels = ["LQ", "SQ", "HQ"]

        def sort_quality(level: list[str]):
            """Sort the quality levels"""
            name = level[0]
            if not name:
                return 0
            parts = name.split("-")
            value = 0
            if self.ab_type == HDRI:
                if "TONEMAPPED" in name:
                    value += 100
            elif self.ab_type == MODEL:
                try:
                    value += model_levels.index(parts[0])
                except ValueError:
                    pass

            if self.ab_type in {HDRI, MATERIAL}:
                qual = parts[0].split("K")[0].split("k")[0]
                try:
                    value += int(qual)
                except ValueError as e:
                    print(
                        f"Error sorting quality levels for asset {self.ab_name}, quality_level '{qual}':\n{format_exc()}"
                    )
            return value

        self.ab_quality_levels.sort(key=sort_quality)

        # Setup info for the metadata panel
        self.ab_metadata = [
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
            self.ab_metadata.append(
                Metadata(
                    "Dimensions",
                    [[data["dimensionX"], data["dimensionY"], data["dimensionZ"]]],
                    to_string=dimensions_to_string,
                )
            )

        self.ab_metadata.append(
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

    def poll(self):
        # These are models with a weird format.
        if any(q in {"HQ", "SQ", "LQ"} for q in self.quality_data):
            return inspect.cleandoc(
                """
            This model has an unsupported format. This should be fixed by Ambient CG in the future,
            but currently this model cannot be imported. If you want it to be fixed faster,
            consider donating to their Patreon so that they have the resources to continue :).
            """
            )
        # if any of the quality levels do not have a name
        elif not all(q[0] != "" for q in self.ab_quality_levels):
            return inspect.cleandoc(
                """
            This asset has corrupted or incomplete quality data, and as such cannot be used.
            """
            )
        elif self.ab_idname in {"acg_3DRock002", "acg_3DRock003", "acg_3DRock004"}:
            return inspect.cleandoc(
                """
            This asset is currently not supported.
            """
            )
        return ""

    def download_preview(self):
        # url = f"https://cdn3.struffelproductions.com/file/ambientCG/media/sphere/128-PNG/{self.ab_name}_PREVIEW.png"
        url = f"https://acg-media.struffelproductions.com/file/ambientCG-Web/media/thumbnail/128-JPG-242424/{self.ab_name}.jpg"
        download_file(url, self.previews_dir, self.preview_name)

    def get_high_res_urls(self) -> list[str]:
        # url = f"https://cdn3.struffelproductions.com/file/ambientCG/media/sphere/1024-JPG-242424/{self.ab_name}_PREVIEW.jpg"
        url = f"https://acg-media.struffelproductions.com/file/ambientCG-Web/media/thumbnail/1024-JPG-242424/{self.ab_name}.jpg"
        return [url]
