from bpy.types import Material, Object, World
from ..asset_utils import HDRI, MATERIAL, MODEL, dimensions_to_string, download_file
from .acg_asset import ACG_Asset
from ..asset_types import AssetListItem, AssetMetadataItem as Metadata


class ACG_AssetListItem(AssetListItem):

    def __init__(self, name: str, data: dict):
        self.name = name
        self.idname = name
        self.label = name  # TODO: make this a more human friendly name
        self.asset_type = ACG_Asset
        self.authors = "Lennart Demes"

        asset_types = {"HDRI": HDRI, "Material": MATERIAL, "3DModel": MODEL}
        bl_types = {"HDRI": World, "Material": Material, "3DModel": Object}

        data_type = data["dataType"]
        self.asset_type = asset_types[data_type]
        self.bl_type = bl_types[data_type]

        self.tags = data["tags"]

        names = {"HDRI": "HDRIs", "Material": "Materials", "3DModel": "Models"}
        self.catalog_path = f"{names[data_type]}/{self.tags[0]}"

        self.metadata = [
            Metadata(
                "Link",
                "AmbientCG",
                "wm.url_open",
                operator_kwargs={"url": f"https://ambientcg.com/view?id={data['assetId']}"},
            ),
            Metadata("type", data["dataType"]),
            Metadata("Downloads", str(data["downloadCount"])),
            Metadata("Release date", data["releaseDate"]),
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

    def download_preview(self):
        url = f"https://cdn3.struffelproductions.com/file/ambientCG/media/sphere/128-PNG/{self.name}_PREVIEW.png"
        download_file(url, self.previews_dir, self.preview_name)
