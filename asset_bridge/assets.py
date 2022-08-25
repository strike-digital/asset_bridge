import json
import bpy
import os
from pathlib import Path
from threading import Thread
from bpy.types import Context
from mathutils import Vector as V
from collections import OrderedDict as ODict
from time import perf_counter

from .constants import PREVIEWS_DIR, DIRS, FILES
from .helpers import Progress, download_preview, main_thread_timer, update_prop,\
    force_ui_update, run_in_main_thread, download_file, file_name_from_url
from .vendor import requests

singular = {
    "all": "all",
    "hdris": "hdri",
    "textures": "texture",
    "models": "model",
}
plural = {y: x for x, y in singular.items()}


class AssetList:

    def __init__(self, list_file: Path, update_list: bool = False, asset_list: dict = {}):
        self.list_file = list_file
        self.sorted = False
        if update_list:
            self.update()

            return

        # load from file if no list provided
        if list_file.exists() and not asset_list:
            with open(list_file, "r") as f:
                asset_list = json.load(f)

        # if no file found and no list provided, download from interntet
        if asset_list:
            self.hdris = asset_list["hdris"]
            self.textures = asset_list["textures"]
            self.models = asset_list["models"]
            self.all = self.hdris | self.textures | self.models

            self.update_categories()
        else:
            # Download from the internet
            self.update()

    def update_category(self, url_type: str):
        result = requests.get(f"https://api.polyhaven.com/assets?t={url_type}").json()
        setattr(self, url_type, ODict(result))

    def update_categories(self):
        self.hdri_categories = {c for a in self.hdris.values() for c in a["categories"]}
        self.hdri_tags = {t for a in self.hdris.values() for t in a["tags"]}

        self.texture_categories = {c for a in self.textures.values() for c in a["categories"]}
        self.texture_tags = {t for a in self.textures.values() for t in a["tags"]}

        self.model_categories = {c for a in self.models.values() for c in a["categories"]}
        self.model_tags = {t for a in self.models.values() for t in a["tags"]}

        self.all_categories = self.hdri_categories | self.texture_categories | self.model_categories
        self.all_tags = self.hdri_tags | self.texture_tags | self.model_tags

    def update(self):
        # using threading here is more complicated, but about 2x as fast,
        # which is important if it is executed at startup
        threads = [
            Thread(target=self.update_category, args=["hdris"]),
            Thread(target=self.update_category, args=["textures"]),
            Thread(target=self.update_category, args=["models"]),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.all: ODict = self.hdris | self.textures | self.models

        self.update_categories()

        data = {"hdris": self.hdris, "textures": self.textures, "models": self.models}
        with open(self.list_file, "w") as f:
            json.dump(data, f, indent=2)

        self.sorted = False

    def sort(self, method: str = "NAME", ascending=False):

        # for a list of all queriable attributes, see the contents of asset_list.json
        accepted = {"hdris", "textures", "models"}
        if method == "NAME":

            def sort(item):
                return item[0].lower()

            ascending = not ascending
        elif method == "DOWNLOADS":

            def sort(item):
                return item[1]["download_count"]
        elif method == "DATE":

            def sort(item):
                return item[1]["date_published"]
        elif method == "AUTHOR":

            def sort(item):
                return list(item[1]["authors"])[0]
        elif method == "AUTHOR":

            def sort(item):
                return list(item[1]["authors"])[0]
        elif method == "EVS":

            def sort(item):
                return item[1]["evs_cap"]

            accepted = {"hdris"}
        elif method == "DIMENSIONS":

            def sort(item):
                return sum(item[1]["dimensions"])

            accepted = {"textures"}

        for category in accepted:
            category_dict: dict = getattr(self, category)
            setattr(self, category, ODict(sorted(category_dict.items(), key=sort, reverse=not ascending)))
        # self.hdris = ODict(sorted(self.hdris.items(), key=sort, reverse=not ascending))
        # if method not in {"EVS"}:
        #     self.textures = ODict(sorted(self.textures.items(), key=sort, reverse=not ascending))
        #     self.models = ODict(sorted(self.models.items(), key=sort, reverse=not ascending))
        self.all = self.hdris | self.textures | self.models
        # self.all = ODict(sorted(self.all.items(), key=sort, reverse=not ascending))
        self.sorted = True

    def get_asset_category(self, asset_name):
        data = self.all[asset_name]
        types = {0: "hdris", 1: "textures", 2: "models"}
        return singular[types[data["type"]]]

    def download_n_previews(self, names, reload, load, size=128):
        for name in names:
            download_preview(name, reload=reload, size=size, load=load)
            self.progress.increment()

    def download_all_previews(self, reload: bool = False):
        start = perf_counter()
        directory = PREVIEWS_DIR
        if reload:
            for file in directory.iterdir():
                os.remove(file)

        files = {f.name.split(".")[0] for f in PREVIEWS_DIR.iterdir()}
        names = {n for n in self.all if n not in files}
        # names = set(list(names)[:10])
        ab = bpy.context.scene.asset_bridge
        self.progress = Progress(len(names), ab, "preview_download_progress")
        main_thread_timer.interval = .1
        update_prop(ab, "download_status", "DOWNLOADING_PREVIEWS")
        force_ui_update()

        threads: list[Thread] = []
        chunk_size = 50
        chunked_list = [list(names)[i:i + chunk_size] for i in range(0, len(names), chunk_size)]
        for assets in chunked_list:
            thread = Thread(
                target=self.download_n_previews,
                args=[assets],
                kwargs={
                    "reload": reload,
                    "load": True
                },
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # report the time in the footer bar
        end = perf_counter()
        run_in_main_thread(
            bpy.ops.asset_bridge.report_message,
            ["INVOKE_DEFAULT"],
            {"message": f"Downloaded {len(names)} assets in {end-start:.2f} seconds"},
        )

        update_prop(ab, "download_status", "NONE")
        force_ui_update()
        main_thread_timer.interval = 1


class Asset:

    def __init__(self, asset_name: str, asset_data: dict = None):
        if asset_data is None:
            asset_data = {}
        start = perf_counter()
        self.asset_webpage_url = f"https://polyhaven.com/a/{asset_name}"
        self.download_progress = None
        self.download_max = 0
        self.name = asset_name
        self.update(asset_data)
        # print(f"Asset info '{asset_name}' downloaded in {perf_counter() - start:.3f}")

    def update(self, asset_data=None):
        if asset_data is None:
            asset_data = {}
        asset_name = self.name
        self.category = asset_list.get_asset_category(asset_name)
        self.data = asset_data or requests.get(f"https://api.polyhaven.com/files/{asset_name}").json()
        self.download_dir = download = getattr(DIRS, plural[self.category])
        self.file_paths = {
            q: download / f"{self.name}_{q}{'.exr' if self.category=='hdri' else '.blend'}"
            for q in self.get_quality_dict()
        }

        force_ui_update()
        list_data = asset_list.all[asset_name]
        self.date_published: int = list_data["date_published"]
        self.categories: list = list_data["categories"]
        self.tags: list = list_data["tags"]
        self.authors: dict = ODict(list_data["authors"])
        self.download_count: int = list_data["download_count"]
        if self.category == "hdri":
            self.whitebalance: int = list_data["whitebalance"] if "whitebalance" in list_data else -1

            self.evs: int = list_data["evs_cap"]
            self.date_taken: int = list_data["date_taken"]
        if self.category == "texture":
            self.dimensions: V = V(list_data["dimensions"])

    def get_file_path(self, quality):
        return self.file_paths[quality]

    def get_quality_dict(self) -> dict:
        return self.data["hdri"] if "hdri" in self.data else self.data["blend"]

    def get_texture_urls(self, quality: str) -> list[str]:
        quality_dict = self.get_quality_dict()[quality]
        return [t["url"] for t in quality_dict["blend"]["include"].values()]

    def get_asset_url(self, quality, file_format):
        quality_dict = self.get_quality_dict()[quality]
        return quality_dict[file_format]["url"]

    def get_blend_url(self, quality: str) -> str:
        return self.get_asset_url(quality, "blend")

    def get_hdri_url(self, quality: str) -> str:
        return self.get_asset_url(quality, "exr")

    def download_asset_file(self, url, dir, file_name=""):
        if file_name:
            download_file(url, dir, file_name)
        else:
            download_file(url, dir)
        self.download_progress.increment()
        # bpy.data.window_managers[0].progress_update(self.download_progress)

    def download_hdri(self, context: Context, quality: str, reload: bool):
        download_max = 1
        self.download_progress = Progress(download_max, context.scene.asset_bridge, "import_progress")

        # Using threading here makes this soooo much faster
        asset_path = self.get_file_path(quality)
        if not asset_path.exists() or reload:
            asset_url = self.get_hdri_url(quality)
            self.download_asset_file(asset_url, dir=asset_path.parent, file_name=asset_path.name)
        return asset_path

    def download_texture(self, context: Context, quality: str, reload: bool):
        asset_path = self.get_file_path(quality)
        download_max = len(list(self.get_quality_dict().values())[0]["blend"]["include"].values()) + 1

        self.download_progress = Progress(download_max, context.scene.asset_bridge, "import_progress")

        # Download the blend file
        # Using threading here makes this soooo much faster
        file_name = asset_path.name
        asset_dir = asset_path.parent
        threads = []
        if not asset_path.exists() or reload:
            if self.category == "hdri":
                asset_url = self.get_hdri_url(quality)
            else:
                asset_url = self.get_blend_url(quality)
            thread = Thread(target=self.download_asset_file, args=(asset_url, asset_dir, file_name))

            threads.append(thread)
            thread.start()
        if self.category != "hdri":
            texture_urls = self.get_texture_urls(quality)
            texture_dir = getattr(DIRS, f"{self.category}_textures")
            for texture_url in texture_urls:
                if not (texture_dir / file_name_from_url(texture_url)).exists() or reload:
                    thread = Thread(target=self.download_asset_file, args=(texture_url, texture_dir))

                    threads.append(thread)
                    thread.start()
        for thread in threads:
            thread.join()
        return asset_path

    def download_asset(self, context: Context, quality: str = "1k", reload: bool = False, format="") -> str:
        asset_path = self.get_file_path(quality)
        if self.category == "hdri":
            return self.download_hdri(context, quality, reload)
        else:
            download_max = len(list(self.get_quality_dict().values())[0]["blend"]["include"].values()) + 1

        self.download_progress = Progress(download_max, context.scene.asset_bridge, "import_progress")

        # Download the blend file
        # Using threading here makes this soooo much faster
        file_name = asset_path.name
        asset_dir = asset_path.parent
        threads = []
        if not asset_path.exists() or reload:
            if self.category == "hdri":
                asset_url = self.get_hdri_url(quality)
            else:
                asset_url = self.get_blend_url(quality)
            thread = Thread(target=self.download_asset_file, args=(asset_url, asset_dir, file_name))

            threads.append(thread)
            thread.start()
        if self.category != "hdri":
            texture_urls = self.get_texture_urls(quality)
            texture_dir = getattr(DIRS, f"{self.category}_textures")
            for texture_url in texture_urls:
                if not (texture_dir / file_name_from_url(texture_url)).exists() or reload:
                    thread = Thread(target=self.download_asset_file, args=(texture_url, texture_dir))

                    threads.append(thread)
                    thread.start()
        for thread in threads:
            thread.join()
        return asset_path

    def import_hdri(self, context: Context, asset_file: Path, quality: str):
        if (context.scene.world and context.scene.use_nodes) or not context.scene.world:
            world = bpy.data.worlds.new(self.name)
        else:
            world = context.scene.world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        if nodes:
            nodes.clear()
            out_node = nodes.new("ShaderNodeOutputWorld")
            background_node = nodes.new("ShaderNodeBackground")
            links.new(background_node.outputs[0], out_node.inputs[0])

        background_node = nodes.get("Background")
        hdri_node = nodes.new("ShaderNodeTexEnvironment")
        links.new(hdri_node.outputs[0], background_node.inputs[0])
        hdri_image = bpy.data.images.load(str(asset_file))
        hdri_node.image = hdri_image
        context.scene.world = world
        world.name = f"{self.name}_{quality}"
        return world

    def import_texture(self, context: Context, asset_file: Path, link:bool, quality: str):
        with bpy.data.libraries.load(str(asset_file), link=link) as (data_from, data_to):
            for mat in data_from.materials:
                if mat == self.name:
                    data_to.materials.append(mat)
                    break
            else:
                data_to.materials.append(data_from.materials[0])
        if obj := context.object:
            if not obj.material_slots:
                obj.data.materials.append(None)
            obj.material_slots[0].material = data_to.materials[0]

        data_to.materials[0].name = f"{self.name}_{quality}"
        return data_to.materials[0]

    def import_model(self, context: Context, asset_file: Path, link: bool, quality: str, location=(0, 0, 0)):
        with bpy.data.libraries.load(filepath=str(asset_file), link=link) as (data_from, data_to):
            # import objects with the correct name, or if none are found, just import all objects
            found = [obj for obj in data_from.objects if self.name in obj]
            if not found:
                found = data_from.objects
            data_to.objects = found

        # Set the selection and remove imported objects that arent meshes
        for obj in bpy.data.objects:
            obj.select_set(False)
        final_obj = None
        for obj in data_to.objects:
            if obj.type == "MESH":
                obj.location = obj.location + V(location)
                context.collection.objects.link(obj)
                obj.select_set(True)
                obj.name = f"{self.name}_{quality}"
                context.view_layer.objects.active = obj
                final_obj = obj
            else:
                bpy.data.objects.remove(obj)

        # Blender is weird, and without pushing an undo step
        # linking the object to the active collection will cause a crash.
        bpy.ops.ed.undo_push()
        return final_obj

    def import_asset(
            self,
            context: Context,
            link: bool = False,
            quality: str = "1k",
            reload: bool = False,
            format: str = "",
            location=(0, 0, 0),
    ):
        """Import the asset in another thread.
        Args:
            link (bool): Whether to link or append the asset (Only for  models)
            quality (str): The quality of the asset to import. Defaults to "1k".
            reload (bool): Whether to redownload an asset if it has already been downloaded. Defaults to False
            location (tuple): The location to place the imported asset (models only). Defaults to (0, 0, 0).
        """
        update_prop(context.scene.asset_bridge, "download_status", "DOWNLOADING_ASSET")
        run_in_main_thread(force_ui_update, ())

        asset_file = self.download_asset(context, quality, reload, format)
        run_in_main_thread(force_ui_update, ())
        if self.category == "hdri":
            run_in_main_thread(self.import_hdri, (context, asset_file, quality))
        elif self.category == "texture":
            run_in_main_thread(self.import_texture, (context, asset_file, link, quality))
        elif self.category == "model":
            run_in_main_thread(self.import_model, (context, asset_file, link, quality, location.copy()))
        update_prop(context.scene.asset_bridge, "download_status", "NONE")


asset_list = AssetList(FILES["asset_list"])
