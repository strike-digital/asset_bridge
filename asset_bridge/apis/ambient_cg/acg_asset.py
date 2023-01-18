import os
from pathlib import Path
import zipfile

from ...helpers.process import new_blender_process
from ..asset_utils import MODEL, MATERIAL, HDRI, download_file, import_hdri, import_model, import_material
from bpy.types import Context
from ..asset_types import Asset, AssetListItem as ACG_AssetListItem

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .acg_asset_list_item import ACG_AssetListItem  # noqa F811


class ACG_Asset(Asset):

    def __init__(self, asset_list_item: ACG_AssetListItem, quality_level: str, link_method: str):
        self.list_item = asset_list_item
        self.name = asset_list_item.name
        self.idname = asset_list_item.idname
        self.type = asset_list_item.type
        self.all_quality_data = asset_list_item.quality_data
        self.quality_data = self.all_quality_data[quality_level]
        self.quality_level = quality_level
        self.link_method = link_method

        self.file_name = f"{self.name}_{self.quality_level}"
        self.blend_file = self.download_dir / f"{self.file_name}.blend"

        self.file_type = self.quality_data["file_type"]

    def get_download_size(self, quality_level: str):
        return self.all_quality_data[quality_level]["size"]

    def download_asset(self):
        file_name = f"{self.file_name}.{self.file_type}"
        url = f"https://ambientcg.com/get?file={file_name}"
        file = download_file(url, self.download_dir, file_name)

        # Unzip
        if self.file_type == "zip":
            with zipfile.ZipFile(file, 'r') as zip:
                zip.extractall(file.parent)

            # Remove unnecessary files
            for file in file.parent.iterdir():
                if file.suffix in {".zip", ".usda", ".usdc"} or any(s in file.name for s in {"_PREVIEW", "NormalDX"}):
                    os.remove(file)

        # Set up a blend file for this asset
        if self.type == MODEL:
            process = new_blender_process(
                script=Path(__file__).parent / "scripts" / "acg_setup_asset.py",
                script_args=("--name", self.name, "--output_file", str(self.blend_file)),
                use_stdout=False,
            )

            process.wait()

    def import_asset(self, context: Context):

        if self.type == HDRI:
            world = import_hdri(self.get_files()[0], f"{self.name}_{self.quality_level}", self.link_method)
            context.scene.world = world
            return world

        elif self.type == MATERIAL:
            # Create a dict with the correct keys for each file
            files = self.get_files()
            texture_types = {
                "Color": "diffuse",
                "AmbientOcclusion": "ao",
                "Displacement": "displacement",
                "NormalGL": "normal",
                "Normal": "normal",
                "Roughness": "roughness",
                "Metalness": "metalness",
                "Metallness": "metalness",
                "Emission": "emission",
                "Opacity": "opacity",
            }
            texture_files = {}

            for file in files:
                texture_type = file.stem.split("_")[-1]
                try:
                    texture_files[texture_types[texture_type]] = file
                except KeyError:
                    # As a fallback, use as a diffuse texture if none is provided
                    if not texture_files.get("diffuse"):
                        texture_files["diffuse"] = file
                    print(f"Asset Bridge: File has an unknown texture type '{texture_type}'")

            mat = import_material(texture_files=texture_files, name=self.name, link_method=self.link_method)
            return mat

        elif self.type == MODEL:
            obj = import_model(context, self.blend_file, self.name, self.link_method)
            return obj

    def download_and_import_asset(self):
        return
