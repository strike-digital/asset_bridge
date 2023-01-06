from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING

from bpy.types import Context

from ..asset_utils import HDRI, MATERIAL, MODEL, download_file, file_name_from_url, import_hdri, import_model, import_material
from ..asset_types import Asset, AssetListItem as PH_AssetListItem
from ...operators.op_report_message import report_message
from ...helpers.process import new_blender_process
from ...vendor import requests

if TYPE_CHECKING:
    from .ph_asset_list_item import PH_AssetListItem  # noqa F811


class PH_Asset(Asset):
    """The Poly Haven asset is a bit different because it sometimes needs to be created in order to
    get information about the available quality levels of the asset. As such, the quality_level and link_method
    arguments are optional here, as opposed to the others where they are required."""

    def __init__(self, asset_list_item: PH_AssetListItem, quality_level: str = "", link_method: str = ""):
        self.list_item = asset_list_item
        self.name = asset_list_item.name
        self.idname = asset_list_item.idname
        self.type = asset_list_item.type

        if quality_level:
            self.quality_level = quality_level
        if link_method:
            self.link_method = link_method

        # example: https://api.polyhaven.com/files/carrot_cake
        self.raw_data = requests.get(f"https://api.polyhaven.com/files/{self.name}").json()

    @property
    def downloads_path(self):
        return self.list_item.downloads_dir / self.quality_level

    def get_quality_data(self) -> dict[str, dict]:
        data = self.raw_data
        if self.type == HDRI:
            return data["hdri"]
        elif self.type in {MATERIAL, MODEL}:
            return data["blend"]

    def get_files_to_download(self, quality_level: str) -> list[dict]:
        data = self.get_quality_data()[quality_level]
        if self.type == HDRI:
            return [data["exr"]]
        else:
            files = []
            files = list(data["blend"]["include"].values())
            if self.type == MODEL:
                files.append(data["blend"])
            return files

    def get_download_size(self, quality_level: str):
        return sum([f["size"] for f in self.get_files_to_download(quality_level)])

    def download_asset(self):
        if not self.quality_level:
            raise ValueError(f"Cannot download {self.name} without providing a quality level")

        urls = self.get_files_to_download(self.quality_level)
        urls = [f["url"] for f in urls]
        paths: list[Path] = []
        for url in urls:
            if self.type == MODEL and not url.endswith(".blend"):
                paths.append(self.download_dir / "textures")
            else:
                paths.append(self.download_dir)

        threads = []

        # Download all of the files in separate threads
        for path, url in zip(paths, urls):
            path.mkdir(parents=True, exist_ok=True)
            name = file_name_from_url(url) if not url.endswith(".blend") else self.name + ".blend"
            thread = Thread(target=download_file, args=(url, path, name))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Process the downloaded blend file if needed
        if self.type == MODEL:

            blend_file = [f for f in self.get_files() if f.suffix == ".blend"][0]
            process = new_blender_process(
                script=Path(__file__).parent / "scripts" / "ph_setup_asset.py",
                script_args=("--name", self.name),
                file=blend_file,
                use_stdout=True,
            )

            process.wait()

            # Handle errors
            out = process.stdout.read().decode()
            if "Error" in out:
                report_message(f"Error setting up Poly Haven asset blend file:\n{out}", severity="ERROR")

    def import_asset(self, context: Context):
        files = self.get_files()

        if self.type == HDRI:
            image_file = files[0]
            world = import_hdri(image_file, name=f"{self.idname}_{self.quality_level}", link_method=self.link_method)
            context.scene.world = world
            return world

        elif self.type == MATERIAL:
            # Find the files and add them to the dictionary with the correct keys for importing
            texture_files = {}
            files = {f.stem: f for f in files}
            associations = {"diffuse": "diff", "displacement": "disp", "normal": "nor_gl", "roughness": "rough"}

            for name, ph_name in associations.items():
                file = files.get(f"{self.name}_{ph_name}_{self.quality_level}")
                if file:
                    texture_files[name] = file

            mat = import_material(texture_files, f"{self.name}_{self.quality_level}", link_method=self.link_method)
            return mat

        elif self.type == MODEL:
            blend_file = [f for f in files if str(f).endswith(".blend")][0]
            imported = import_model(context, blend_file, name=self.name, link_method=self.link_method)
            return imported

    def download_and_import_asset(self):
        return
