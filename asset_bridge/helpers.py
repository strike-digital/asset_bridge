import json
import shutil
from queue import Queue
from pathlib import Path
from threading import Thread
from functools import partial
from dataclasses import dataclass

import bpy
from bpy.utils import previews
from bpy.props import StringProperty
from bpy.types import AddonPreferences, Context, Operator

from .vendor import requests
from .constants import DIRS, BL_ASSET_LIB_NAME, FILES
"""I apologise if you have to try and understand this mess."""


def update_prefs_file():
    with open(FILES.prefs_file, "w") as f:
        json.dump({"lib_path": get_prefs(bpy.context).lib_path}, f)


def get_prefs(context: Context) -> AddonPreferences:
    return context.preferences.addons[__package__].preferences


def get_icon(name: str):
    return pcolls["icons"][name]


def file_name_from_url(url: str) -> str:
    return url.split('/')[-1].split("?")[0]


def ui_update_timer(area=None, area_types={"VIEW_3D"}, region_types={"WINDOW", "UI"}):
    if not isinstance(area_types, set):
        area_types = {area_types}
    if not isinstance(region_types, set):
        area_types = {region_types}
    areas = []
    if area:
        areas = [area]
    else:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type not in area_types:
                    continue
                areas.append(area)
    for area in areas:
        for region in area.regions:
            if region.type not in region_types:
                continue
            region.tag_redraw()


def force_ui_update(area=None, area_types={"VIEW_3D", "PREFERENCES"}, region_types={"WINDOW", "UI"}):
    """Sometimes calling tag_redraw doesn't work, but doing it in a timer does"""
    bpy.app.timers.register(partial(ui_update_timer, area, area_types, region_types), first_interval=.00001)


def ensure_asset_library():
    """Check that asset bridge blend is loaded as an asset library in blender, and if not, add it as one."""
    asset_libs = bpy.context.preferences.filepaths.asset_libraries
    for asset_lib in asset_libs:
        if asset_lib.path == str(DIRS.asset_browser):
            break
    else:
        # if BL_ASSET_LIB_NAME not in asset_libs:
        bpy.ops.preferences.asset_library_add()
        asset_libs[-1].name = BL_ASSET_LIB_NAME
        asset_libs[-1].path = str(DIRS.asset_browser)
        bpy.ops.wm.save_userpref()


def asset_preview_exists(name):
    """Whether the preview image for this asset exists"""
    image_path = DIRS.previews / f"{name}.png"
    return image_path.exists()


def download_file(url: str, download_path: Path, file_name: str = "", print_end=True):
    """Download an image from the provided url to the given file path"""
    download_path = Path(download_path)
    download_path.mkdir(exist_ok=True)
    file_name = file_name or file_name_from_url(url)
    download_path = download_path / file_name
    res = requests.get(url, stream=True)
    if res.status_code != 200:
        with open(DIRS.addon / "log.txt", "w") as f:
            f.write(url)
            f.write(res.status_code)
        raise requests.ConnectionError()

    with open(download_path, 'wb') as f:
        shutil.copyfileobj(res.raw, f)
    if print_end:
        print('File sucessfully Downloaded: ', file_name)
    return download_path


downloading_previews = {}


def download_preview(asset_name, reload=False, size=128, load=True):
    downloading_previews[asset_name] = True
    url = f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_name}.png?width={size}&height={size}"

    file_name = f"{asset_name}.png"
    if not (Path(DIRS.previews) / file_name).is_file() or reload:
        download_file(url, DIRS.previews, file_name, print_end=False)
    image_path = DIRS.previews / file_name

    if not load:
        downloading_previews[asset_name] = False
        return image_path
    try:
        pcolls["assets"].load(asset_name, str(image_path), path_type="IMAGE")
    except KeyError as e:
        pcolls["assets"][asset_name].reload()

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


class Progress:

    data = None
    propname = ""

    def __init__(self, max, data=None, propname=""):
        self.max = max
        self.data = data or self.data
        self.propname = propname or self.propname
        self.message = ""
        self.progress = 0

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        prop_val = self.read()
        if getattr(self.data, self.propname) != prop_val:
            update_prop(self.data, self.propname, prop_val)
            force_ui_update()

    def increment(self, value=1):
        self.progress += value
        # setattr(self.data, self.propname, int(self.read()))
        # self.ab.import_progress = int(self.read())

    def read(self):
        return self.progress / self.max * 100


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
    bpy.app.timers.register(main_thread_timer)


def main_thread_timer():
    """Go through the functions in the queue and execute them.
    This is checked every n seconds, where n is the return value"""
    while not main_thread_queue.empty():
        func, args, kwargs = main_thread_queue.get()
        # print(f"executing function '{func.__name__}' on main thread")
        func(*args, **kwargs)
    # return main_thread_timer.interval


main_thread_timer.interval = 1


def update_prop(data, name, value):
    """Update a single blender property in the main thread"""
    run_in_main_thread(setattr, (data, name, value))


pcoll = previews.new()
pcolls = {"assets": pcoll}
pcoll = previews.new()
pcolls["icons"] = pcoll
for file in DIRS.icons.iterdir():
    pcoll.load(file.name.split(".")[0], str(file), path_type="IMAGE")


def register():
    bpy.app.timers.register(main_thread_timer)


def unregister():
    if bpy.app.timers.is_registered(main_thread_timer):
        bpy.app.timers.unregister(main_thread_timer)
    for pcoll in pcolls.values():
        try:
            pcoll.close()
        except KeyError:
            pass


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
                    if props:
                        return props.bl_description
                    else:
                        return op_description
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
