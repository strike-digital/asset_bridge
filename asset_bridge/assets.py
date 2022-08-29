import json
import math
import bpy
import os
import subprocess
from pathlib import Path
from threading import Thread
from bpy.types import Context
from mathutils import Vector as V
from collections import OrderedDict as ODict
from time import perf_counter
from asset_bridge.constants import DIRS, FILES
from asset_bridge.helpers import Progress, download_preview, update_prop,\
    force_ui_update, run_in_main_thread, download_file, file_name_from_url
from asset_bridge.vendor import requests

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
            self.hdris: dict = asset_list["hdris"]
            self.textures: dict = asset_list["textures"]
            self.models: dict = asset_list["models"]
            self.all: dict = self.hdris | self.textures | self.models

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
        directory = DIRS.previews
        if reload:
            for file in directory.iterdir():
                os.remove(file)

        files = {f.name.split(".")[0] for f in DIRS.previews.iterdir()}
        names = {n for n in self.all if n not in files}
        if not names:
            run_in_main_thread(
                bpy.ops.asset_bridge.report_message,
                ["INVOKE_DEFAULT"],
                {"message": "No new assets to download."},
            )
            return

        ab = bpy.context.scene.asset_bridge
        self.progress = Progress(len(names) + len(self.all), ab, "preview_download_progress")
        self.progress.message = "Downloading previews..."
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

        # Set up the asset blend file.
        self.progress.message = "Setting up assets..."

        asset_process = subprocess.Popen([
            bpy.app.binary_path,
            "--factory-startup",
            "-b",
            "--python",
            FILES.setup_asset_library,
        ],)

        with open(FILES.script_progress, "w") as f:
            f.write("0")

        def check_asset_process():
            if asset_process.poll() is not None:
                update_prop(bpy.context.scene.asset_bridge, "download_status", "NONE")
                force_ui_update()

                # report the time in the footer bar
                end = perf_counter()
                run_in_main_thread(
                    bpy.ops.asset_bridge.report_message,
                    ["INVOKE_DEFAULT"],
                    {"message": f"Downloaded {len(names)} assets in {end-start:.2f} seconds"},
                )
                return

            with open(FILES.script_progress, "r") as f:
                if val := f.read():
                    progress = int(val)
                else:
                    return .01

            if self.progress.progress != len(names) + progress:
                self.progress.progress = len(names) + progress
            return .01

        bpy.app.timers.register(check_asset_process, first_interval=.1)


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

    def get_file_path(self, quality) -> Path:
        return self.file_paths[quality]

    def is_downloaded(self, quality: str) -> bool:
        return self.get_file_path(quality).exists()

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

    def download_blend_file(self, url, dir, file_name, script_path):
        """Download the blend file, and then run a script in it."""
        self.download_asset_file(url, dir, file_name)
        if script_path:
            subprocess.run([
                bpy.app.binary_path,
                Path(dir) / file_name,
                "--factory-startup",
                "-b",
                "--python",
                script_path,
            ])

    def download_asset_with_blend_file(self, context: Context, quality: str, reload: bool, script_path: Path = ""):
        """Download an asset that has a blend file and textures (aka texture and model assets)"""
        download_max = len(list(self.get_quality_dict().values())[0]["blend"]["include"].values()) + 1

        self.download_progress = Progress(download_max, context.scene.asset_bridge, "import_progress")

        # Download the blend file
        # Using threading here makes this soooo much faster
        threads = []
        asset_path = self.get_file_path(quality)
        if not asset_path.exists() or reload:
            asset_url = self.get_blend_url(quality)
            thread = Thread(
                target=self.download_blend_file,
                args=(asset_url, asset_path.parent, asset_path.name, script_path),
            )
            threads.append(thread)
            thread.start()

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
        return self.download_asset_with_blend_file(context, quality, reload)

    def download_model(self, context: Context, quality: str, reload: bool):
        return self.download_asset_with_blend_file(
            context,
            quality,
            reload,
            script_path=FILES.setup_model_blend,
        )

    def download_asset(self, context: Context, quality: str = "1k", reload: bool = False) -> str:
        if self.category == "hdri":
            return self.download_hdri(context, quality, reload)
        elif self.category == "texture":
            return self.download_texture(context, quality, reload)
        elif self.category == "model":
            return self.download_model(context, quality, reload)

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

    def import_texture(self, context: Context, asset_file: Path, link: bool, quality: str, material_slot=""):
        with bpy.data.libraries.load(str(asset_file), link=link) as (data_from, data_to):
            for mat in data_from.materials:
                if mat == self.name:
                    data_to.materials.append(mat)
                    break
            else:
                data_to.materials.append(data_from.materials[0])

        if obj := context.object:
            obj: bpy.types.Object
            if not material_slot:
                if not obj.material_slots:
                    obj.data.materials.append(None)
                material_slot = obj.material_slots[obj.active_material_index]
            material_slot.material = data_to.materials[0]

        data_to.materials[0].name = f"{self.name}_{quality}"
        return data_to.materials[0]

    def import_model(self, context: Context, asset_file: Path, link: bool, quality: str, location=(0, 0, 0)):
        with bpy.data.libraries.load(filepath=str(asset_file), link=link) as (data_from, data_to):
            # import objects with the correct name, or if none are found, just import all objects
            for coll in data_from.collections:
                if coll == f"{self.name}_{quality}":
                    data_to.collections.append(coll)
                    break
            # found = [obj for obj in data_from.objects if self.name in obj]
            # if not found:
            #     found = data_from.objects
            # data_to.objects = found
        for obj in bpy.data.objects:
            obj.select_set(False)

        collection: bpy.types.Collection = data_to.collections[0]
        if link:
            empty = bpy.data.objects.new(collection.name, None)
            empty.instance_type = "COLLECTION"
            empty.instance_collection = collection
            context.collection.objects.link(empty)
            empty.empty_display_size = math.hypot(*list(collection.objects[0].dimensions))
            empty.select_set(True)
            final_obj = empty
        else:
            context.collection.children.link(collection)

            # Set the selection and remove imported objects that arent meshes
            final_obj = None
            for obj in collection.objects:
                obj.location += V(location)
                obj.select_set(True)
                obj.name = f"{self.name}_{quality}"
                final_obj = obj

        context.view_layer.objects.active = final_obj
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
            material_slot: bpy.types.MaterialSlot = None,
            location: tuple[int] = (0, 0, 0),
            on_completion=None,
    ):
        """Import the asset in another thread.
        Args:
            link (bool): Whether to link or append the asset (Only for  models)
            quality (str): The quality of the asset to import. Defaults to "1k".
            reload (bool): Whether to redownload an asset if it has already been downloaded. Defaults to False
            location (tuple): The location to place the imported asset (models only). Defaults to (0, 0, 0).
        """

        import_only = self.is_downloaded(quality) and not reload

        if not import_only:
            update_prop(context.scene.asset_bridge, "download_status", "DOWNLOADING_ASSET")
            run_in_main_thread(force_ui_update, ())

        asset_file = self.download_asset(context, quality, reload)
        if not import_only:
            run_in_main_thread(force_ui_update, ())

        if self.category == "hdri":
            run_in_main_thread(self.import_hdri, (context, asset_file, quality))
        elif self.category == "texture":
            run_in_main_thread(self.import_texture, (context, asset_file, link, quality, material_slot))
        elif self.category == "model":
            run_in_main_thread(self.import_model, (context, asset_file, link, quality, location.copy()))
        if on_completion:
            run_in_main_thread(on_completion, ())
        if not import_only:
            update_prop(context.scene.asset_bridge, "download_status", "NONE")


asset_list = AssetList(FILES.asset_list)
