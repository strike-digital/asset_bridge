from collections import OrderedDict as ODict
from functools import partial
import json
import os
from time import perf_counter
import bpy
import shutil
from pathlib import Path
from .vendor import requests
from .constants import BL_ASSET_LIB_NAME, DIRS, FILES, ICONS_DIR, PREVIEWS_DIR
from bpy.types import Context, AddonPreferences, Operator
from bpy.props import StringProperty
from bpy.utils import previews
from threading import Thread
from mathutils import Vector as V
from dataclasses import dataclass
from queue import Queue
"""I apologise if you have to try and understand this mess."""


def get_prefs(context: Context) -> AddonPreferences:
    return context.preferences.addons[__package__].preferences


def get_icon(name: str):
    return pcolls["icons"][name]


def file_name_from_url(url: str) -> str:
    return url.split('/')[-1].split("?")[0]


def ui_update_timer(all):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            region_type = "WINDOW" if area.type == "PREFERENCES" else "UI"
            for region in area.regions:
                if region.type == region_type or all:
                    region.tag_redraw()


def force_ui_update(all=False):
    """Sometimes calling tag_redraw doesn't work, but doing it in a timer does"""
    bpy.app.timers.register(partial(ui_update_timer, all), first_interval=.00001)


def ensure_asset_library():
    """Check that asset bridge blend is loaded as an asset library in blender, and if not, add it as one."""
    asset_libs = bpy.context.preferences.filepaths.asset_libraries
    if BL_ASSET_LIB_NAME not in asset_libs:
        bpy.ops.preferences.asset_library_add()
        asset_libs[-1].name = BL_ASSET_LIB_NAME
        asset_libs[-1].path = str(FILES["asset_lib_blend"])


def asset_preview_exists(name):
    """Whether the preview image for this asset exists"""
    image_path = PREVIEWS_DIR / f"{name}.png"
    return image_path.exists()


def download_file(url: str, download_path: Path, file_name: str = ""):
    """Download an image from the provided url to the given file path"""
    download_path = Path(download_path)
    download_path.mkdir(exist_ok=True)
    file_name = file_name or file_name_from_url(url)
    download_path = download_path / file_name
    res = requests.get(url, stream=True)
    if res.status_code != 200:
        with open(Path.cwd() / "log.txt", "w") as f:
            f.write(url)
            f.write(res.status_code)
        raise requests.ConnectionError()
    with open(download_path, 'wb') as f:
        shutil.copyfileobj(res.raw, f)
    print('File sucessfully Downloaded: ', file_name)
    return download_path


downloading_previews = {}


def download_preview(asset_name, reload=False, size=128, load=True):
    downloading_previews[asset_name] = True
    url = f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_name}.png?width={size}&height={size}"

    file_name = f"{asset_name}.png"
    if not (Path(PREVIEWS_DIR) / file_name).is_file() or reload:
        download_file(url, PREVIEWS_DIR, file_name)
    image_path = PREVIEWS_DIR / file_name

    if not load:
        downloading_previews[asset_name] = False
        return image_path
    try:
        pcolls["assets"].load(asset_name, str(image_path), path_type="IMAGE")
    except KeyError as e:
        pcolls["assets"][asset_name].reload()

    # We need to update the UI once the preview has been loaded
    force_ui_update()
    downloading_previews[asset_name] = False


def get_asset_preview(asset_name: str, reload: bool = False, size: int = 128):
    if asset_name not in pcolls["assets"]:
        if asset_name in downloading_previews:
            return 0

        # Start the download process on a different thread to prevent locking up the UI
        # In general, this isn't a good idea with blender, but since we aren't modifi
        thread = Thread(target=download_preview, args=[asset_name, reload, size, True])
        thread.start()
        return 0
    else:
        pcoll = pcolls["assets"][asset_name]
    return pcoll.icon_id


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

        if method == "NAME":
            ascending = not ascending

            def sort(item):
                return item[0].lower()
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

        self.hdris = ODict(sorted(self.hdris.items(), key=sort, reverse=not ascending))
        if method not in {"EVS"}:
            self.textures = ODict(sorted(self.textures.items(), key=sort, reverse=not ascending))
            self.models = ODict(sorted(self.models.items(), key=sort, reverse=not ascending))
        self.all = self.hdris | self.textures | self.models
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


class Progress:

    def __init__(self, max, data, propname):
        self.total = 0
        self.max = max
        self.data = data
        self.propname = propname
        # setattr(self.data, self.propname, 0)
        update_prop(self.data, self.propname, 0)
        force_ui_update()

    def increment(self, value=1):
        force_ui_update()
        self.total += value
        update_prop(self.data, self.propname, int(self.read()))
        # setattr(self.data, self.propname, int(self.read()))
        # self.ab.import_progress = int(self.read())

    def read(self):
        return self.total / self.max * 100


class Asset:

    def __init__(self, asset_name: str, asset_data: dict = None):
        if asset_data is None:
            asset_data = {}
        start = perf_counter()
        self.download_progress = None
        self.download_max = 0
        self.name = asset_name
        self.update(asset_data)
        print(f"Asset info '{asset_name}' downloaded in {perf_counter() - start:.3f}")

    def update(self, asset_data=None):
        if asset_data is None:
            asset_data = {}
        asset_name = self.name
        self.category = asset_list.get_asset_category(asset_name)
        self.data = asset_data or requests.get(f"https://api.polyhaven.com/files/{asset_name}").json()

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

    def download_asset(self, context: Context, quality: str = "1k", reload: bool = False, file_format: str = "") -> str:
        if not file_format:
            file_format = ".exr" if self.category == "hdri" else ".blend"
        elif self.category == "hdri" and file_format not in [".exr", ".hdr"]:
            raise ValueError(f"Invalid format: '{file_format}'")
        file_name = self.name + file_format
        if self.category == "hdri":
            download_max = 1
        else:
            download_max = len(list(self.get_quality_dict().values())[0]["blend"]["include"].values()) + 1

        self.download_progress = Progress(download_max, context.scene.asset_bridge, "import_progress")

        # Download the blend file
        # Using threading here makes this soooo much faster
        asset_dir = DIRS[plural[self.category]]
        asset_path = asset_dir / file_name
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
            texture_dir = DIRS[f"{self.category}_textures"]
            for texture_url in texture_urls:
                if not (texture_dir / file_name_from_url(texture_url)).exists() or reload:
                    thread = Thread(target=self.download_asset_file, args=(texture_url, texture_dir))

                    threads.append(thread)
                    thread.start()
        for thread in threads:
            thread.join()
        return asset_path

    def import_hdri(self, context: Context, asset_file: Path):
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
        return world

    def import_texture(self, context: Context, asset_file: Path):
        with bpy.data.libraries.load(str(asset_file)) as (data_from, data_to):
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
        return data_to.materials[0]

    def import_model(self, context: Context, asset_file: Path, location=(0, 0, 0)):
        with bpy.data.libraries.load(str(asset_file)) as (data_from, data_to):
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
                context.scene.collection.objects.link(obj)
                obj.select_set(True)
                context.view_layer.objects.active = obj
                final_obj = obj
            else:
                bpy.data.objects.remove(obj)
        return final_obj

    def import_asset(
            self,
            context: Context,
            quality: str = "1k",
            reload: bool = False,
            format: str = "",
            location=(0, 0, 0),
    ):
        update_prop(context.scene.asset_bridge, "download_status", "DOWNLOADING_ASSET")
        run_in_main_thread(force_ui_update, ())

        asset_file = self.download_asset(context, quality, reload, format)
        run_in_main_thread(force_ui_update, ())
        if self.category == "hdri":
            run_in_main_thread(self.import_hdri, (context, asset_file))
        elif self.category == "texture":
            run_in_main_thread(self.import_texture, (context, asset_file))
        elif self.category == "model":
            run_in_main_thread(self.import_model, (context, asset_file, location.copy()))
        update_prop(context.scene.asset_bridge, "download_status", "NONE")


# It's a bad idea to modify blend data in arbitrary threads,
# so if those threads want to do so, they can add a function to the queue
# which will then be executed on the main thread based on a timer
main_thread_queue = Queue()


def run_in_main_thread(function, args, kwargs=None):
    """Run the given function in the main thread when it is next available.
    This is useful because it is usually a bad idea to modify blend data at arbitrary times on separate threads,
    as this can causes weird error messages, and even crashes."""
    if kwargs is None:
        kwargs = {}
    main_thread_queue.put((function, args, kwargs))


def main_thread_timer():
    """Go through the functions in the queue and execute them.
    This is checked every n seconds, where n is the return value"""
    while not main_thread_queue.empty():
        func, args, kwargs = main_thread_queue.get()
        # print(f"executing function '{func.__name__}' on main thread")
        func(*args, **kwargs)
    return main_thread_timer.interval


main_thread_timer.interval = 1


def update_prop(data, name, value):
    """Update a single blender property in the main thread"""
    run_in_main_thread(setattr, (data, name, value))


start = perf_counter()
asset_file = FILES["asset_list"]
asset_list = AssetList(asset_file)

print(f"Got asset list in: {perf_counter() - start:.3f}s")

pcoll = previews.new()
pcolls = {"assets": pcoll}
pcoll = previews.new()
pcolls["icons"] = pcoll
for file in ICONS_DIR.iterdir():
    pcoll.load(file.name.split(".")[0], str(file), path_type="IMAGE")


def register():
    bpy.app.timers.register(main_thread_timer)


def unregister():
    bpy.app.timers.unregister(main_thread_timer)
    for pcoll in pcolls.values():
        pcoll.close()


@dataclass
class Op():
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    The only required argument is the category of the operator,
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convension ADDON_NAME_OT_operator_name.

    Args:
        `category` (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        `idname` (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        `label` (str): The name of the operator that is displayed in the UI.
        `description` (str): The description of the operator that is displayed in the UI.
        `dynamic_description` (bool): Whether to automatically allow bl_description to be altered from the UI.
        `register` (bool): Whether to display the operator in the info window and support the redo panel.
        `undo` (bool): Whether to push an undo step after the operator is executed.
        `undo_grouped` (bool): Whether to group multiple consecutive executions of the operator into one undo step.
        `internal` (bool): Whether the operator is only used internally and should not be shown in menu search
            (doesn't affect the operator search accessible when developer extras is enabled).
        `wrap_cursor` (bool): Whether to wrap the cursor to the other side of the region when it goes outside of it.
        `wrap_cursor_x` (bool): Only wrap the cursor in the horizontal (x) direction.
        `wrap_cursor_y` (bool): Only wrap the cursor in the horizontal (y) direction.
        `preset` (bool): Display a preset button with the operators settings.
        `blocking` (bool): Block anything else from using the cursor.
        `macro` (bool): Use to check if an operator is a macro.
        `logging` (int | bool): Whether to log when this operator is called.
            Default is to use the class logging variable which can be set with set_logging() and is global.
    """

    _logging = False

    @classmethod
    def set_logging(cls, enable):
        """Set the global logging state for all operators"""
        cls._logging = enable

    category: str
    idname: str = ""
    label: str = ""
    description: str = ""
    dynamic_description: bool = True
    invoke: bool = True
    register: bool = True
    undo: bool = False
    undo_grouped: bool = False
    internal: bool = False
    wrap_cursor: bool = False
    wrap_cursor_x: bool = False
    wrap_cursor_y: bool = False
    preset: bool = False
    blocking: bool = False
    macro: bool = False
    # The default is to use the class logging setting, unless this has a value other than -1.
    # ik this is the same name as the module, but I don't care.
    logging: int = -1

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("OT_")[-1]
        idname = f"{self.category}." + (self.idname or cls_name_end)
        label = self.label or cls_name_end.replace("_", " ").title()

        if self.description:
            op_description = self.description
        elif cls.__doc__:
            op_description = cls.__doc__
        else:
            op_description = label

        options = {
            "REGISTER": self.register,
            "UNDO": self.undo,
            "UNDO_GROUPED": self.undo_grouped,
            "GRAB_CURSOR": self.wrap_cursor,
            "GRAB_CURSOR_X": self.wrap_cursor_x,
            "GRAB_CURSOR_Y": self.wrap_cursor_y,
            "BLOCKING": self.blocking,
            "INTERNAL": self.internal,
            "PRESET": self.preset,
            "MACRO": self.macro,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)
        log = self._logging if self.logging == -1 else bool(self.logging)

        class Wrapped(cls, Operator):
            bl_idname = idname
            bl_label = label
            bl_options = options

            if self.dynamic_description:
                bl_description: StringProperty(default=op_description)

                @classmethod
                def description(cls, context, props):
                    return props.bl_description
            else:
                bl_description = op_description

            if self.invoke:

                def invoke(_self, context, event):
                    """Here we can log whenever an operator using this decorator is invoked"""
                    if log:
                        print(f"Invoke: {idname}")
                    if hasattr(super(), "invoke"):
                        return super().invoke(context, event)
                    else:
                        return _self.execute(context)

        Wrapped.__doc__ = op_description
        Wrapped.__name__ = cls.__name__
        return Wrapped