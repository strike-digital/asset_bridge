import json
import math
from multiprocessing import Process
from pprint import pprint
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

SINGULAR = {
    "all": "all",
    "hdris": "hdri",
    "textures": "texture",
    "models": "model",
}
PLURAL = {y: x for x, y in SINGULAR.items()}
ASSET_TYPES = {0: "hdri", 1: "texture", 2: "model"}

with open(FILES.asset_list, "r") as f:
    try:
        asset_list_raw = json.load(f)
    except Exception:
        asset_list_raw = {}
        pass
try:
    all_assets_raw = asset_list_raw["hdris"] | asset_list_raw["textures"] | asset_list_raw["models"]
except KeyError:
    all_assets_raw = None
    pass


def create_assets(list, names):
    for name in names:
        list.all[name] = Asset(name)


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
            # return
            self.hdris: dict = asset_list_raw["hdris"]
            self.textures: dict = asset_list_raw["textures"]
            self.models: dict = asset_list_raw["models"]
            self.all: dict = self.hdris | self.textures | self.models

            self.update_categories()
        else:
            # Download from the internet
            self.update()

    def update_categories(self):
        self.hdri_categories = {c for a in self.hdris.values() for c in a.categories}
        self.hdri_tags = {t for a in self.hdris.values() for t in a.tags}

        self.texture_categories = {c for a in self.textures.values() for c in a.categories}
        self.texture_tags = {t for a in self.textures.values() for t in a.tags}

        self.model_categories = {c for a in self.models.values() for c in a.categories}
        self.model_tags = {t for a in self.models.values() for t in a.tags}

        self.all_categories = self.hdri_categories | self.texture_categories | self.model_categories
        self.all_tags = self.hdri_tags | self.texture_tags | self.model_tags

    def update_category(self, url_type: str):
        result = requests.get(f"https://api.polyhaven.com/assets?t={url_type}").json()
        setattr(self, url_type, result)
        return
        assets = ODict()

        def create_assets(names):
            for name in names:
                assets[name] = Asset(name)

        threads = []
        chunk_size = 5
        chunks = [list(result)[i:i + chunk_size] for i in range(0, len(result), chunk_size)]
        for names in chunks:
            thread = Thread(target=create_assets, args=[names])
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        setattr(self, url_type, assets)

    def update(self):
        asset_list = requests.get("https://api.polyhaven.com/assets").json()
        # for i in ["hdris", "textures", "models"]:
        #     self.update_category(i)
        # self.all = self.hdris | self.textures | self.models
        # diction = {"hdris": self.hdris, "textures": self.textures, "models": self.models}
        # with open(FILES.asset_list, "w") as f:
        #     json.dump(diction, f, indent=4)
        # return
        self.all = ODict()

        start = perf_counter()

        # def create_assets(names):
        #     for name in names:
        #         self.all[name] = Asset(name)

        threads = []
        chunk_size = 20
        chunks = [list(asset_list)[i:i + chunk_size] for i in range(0, len(asset_list), chunk_size)]
        for names in chunks:
            thread = Thread(target=create_assets, args=[self, names])
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.hdris: dict[str: Asset] = ODict({k: v for k, v in self.all.items() if v.category == "hdri"})
        self.textures = ODict({k: v for k, v in self.all.items() if v.category == "texture"})
        self.models = ODict({k: v for k, v in self.all.items() if v.category == "model"})
        # threads = [
        #     Thread(target=self.update_category, args=["hdris"]),
        #     Thread(target=self.update_category, args=["textures"]),
        #     Thread(target=self.update_category, args=["models"]),
        # ]
        # for thread in threads:
        #     thread.start()
        # for thread in threads:
        #     thread.join()

        # self.all: ODict = self.hdris | self.textures | self.models
        # chunk_size = 5

        # def get_asset(names):
        #     for name in names:
        #         self.ahdris[name] = Asset(name, self)
        #     self.progress.progress += chunk_size

        # self.ahdris = {}
        # threads = []
        # models = list(self.all)
        # self.progress = Progress(len(models), bpy.context.scene.asset_bridge.panel, "preview_download_progress")
        # lst = [models[i:i + chunk_size] for i in range(0, len(self.models), chunk_size)]
        # for names in lst:
        #     thread = Thread(target=get_asset, args=[names])
        #     thread.start()
        #     threads.append(thread)

        # for i, thread in enumerate(threads):
        #     thread.join()
        # print(i)
        # self.ahdris[name] = Asset(name)

        print(f"Done in {perf_counter() - start:.4f}")
        self.update_categories()

        # data = {"hdris": self.hdris, "textures": self.textures, "models": self.models}
        data = self.as_json()
        with open(self.list_file, "w") as f:
            json.dump(data, f, indent=2)

        self.sorted = False
        
    def as_json(self):
        data = {
            "hdris": {k: v.as_json() for k, v in self.hdris.items()},
            "textures": {k: v.as_json() for k, v in self.textures.items()},
            "models": {k: v.as_json() for k, v in self.models.items()},
        }
        return data

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
        return SINGULAR[types[data["type"]]]

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

        ab = bpy.context.scene.asset_bridge.panel
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
                update_prop(bpy.context.scene.asset_bridge.panel, "download_status", "NONE")
                force_ui_update()

                # report the time in the footer bar
                end = perf_counter()
                run_in_main_thread(
                    bpy.ops.asset_bridge.report_message,
                    ["INVOKE_DEFAULT"],
                    {"message": f"Downloaded {len(names)} asset previews in {end-start:.2f} seconds"},
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
        self.asset_webpage_url = f"https://polyhaven.com/a/{asset_name}"
        self.download_progress = None
        self.download_max = 0
        self.name = asset_name
        self.label = all_assets_raw[self.name]["name"]
        self.update(asset_data)

    def update(self, asset_data=None):
        if asset_data is None:
            asset_data = {}
        asset_name = self.name
        # self.category = asset_list.get_asset_category(asset_name)
        self.category = ASSET_TYPES[all_assets_raw[self.name]["type"]]
        self.data = asset_data or self._process_data(requests.get(f"https://api.polyhaven.com/files/{asset_name}").json())
        self.download_dir = download = getattr(DIRS, PLURAL[self.category])
        self.quality_levels = self.data.keys()
        self.file_paths = {
            q: download / f"{self.name}_{q}{'.exr' if self.category=='hdri' else '.blend'}"
            for q in self.quality_levels
        }

        # force_ui_update()
        # list_data = asset_list.all[asset_name]
        list_data = all_assets_raw[self.name]
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

    def _process_data(self, data):
        new_data = {}
        # blend = data["blend"]["blend"]
        try:
            quality_levels = list(data["blend"])
        except KeyError:
            return data
        for q in quality_levels:
            new_data[q] = {}
            if self.category == "hdri":
                hdri = data["hdri"][q]["exr"]
                new_data[q]["url": hdri["url"], "size": hdri["size"]]
            else:
                blend = data["blend"][q]["blend"]
                # new_data[q]["blend"] = {"url": blend["url"], "size": blend["size"]}
                new_data[q]["url"] = blend["url"]
                new_data[q]["size"] = blend["size"]
                new_data[q]["textures"] = {}
                for name, tex in blend["include"].items():
                    new_data[q]["textures"][name] = {"url": tex["url"], "size": tex["size"]}
        return new_data

    def as_json(self):
        return self.data | all_assets_raw[self.name]

    def get_file_path(self, quality) -> Path:
        return self.file_paths[quality]

    def is_downloaded(self, quality: str) -> bool:
        return self.get_file_path(quality).exists()

    def get_texture_urls(self, quality: str) -> list[str]:
        return [t["url"] for t in self.data["textures"].values()]

    def get_asset_url(self, quality, file_format):
        return self.data["url"]

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
        texture_urls = self.get_texture_urls(quality)
        download_max = len(texture_urls) + 1

        self.download_progress = Progress(download_max, context.scene.asset_bridge.panel, "import_progress")

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
        self.download_progress = Progress(download_max, context.scene.asset_bridge.panel, "import_progress")

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
            update_prop(context.scene.asset_bridge.panel, "download_status", "DOWNLOADING_ASSET")
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
            update_prop(context.scene.asset_bridge.panel, "download_status", "NONE")


asset_list = AssetList(FILES.asset_list)
# asset_list.update()
