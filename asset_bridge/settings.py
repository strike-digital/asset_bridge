# from __future__ import annotations
from time import time_ns, perf_counter
from typing import TYPE_CHECKING, OrderedDict

import bpy
from bpy.props import (IntProperty, BoolProperty, EnumProperty, FloatProperty, StringProperty, PointerProperty,
                       CollectionProperty)
from bpy.types import ID, Context, Material, UILayout, PropertyGroup

from .api import get_asset_lists
from .helpers.progress import Progress


def add_progress(cls, name):
    """Add a two properties to the given class; one that can be set by the addon, and one that can be shown in the UI
    This allows for a standard progress look across the addon."""
    kwargs = {"name": "Downloading:", "subtype": "PERCENTAGE", "min": 0, "max": 100, "precision": 0}
    cls.__annotations__[name] = FloatProperty(**kwargs)
    ui_kwargs = kwargs.copy()
    ui_kwargs["set"] = lambda self, value: None
    ui_kwargs["get"] = lambda self: getattr(self, name)
    cls.__annotations__[f"ui_{name}"] = FloatProperty(**ui_kwargs)
    cls.__annotations__[f"{name}_active"] = BoolProperty()


# This is needed to prevent the dynamic enum bug that causes the label of the enum items to go weird:
# https://github.com/3dninjas/3dn-bip/issues/51
_item_map = dict()


def _make_item(id, name, descr, icon="", number=0):
    lookup = f"{str(id)}\0{str(name)}\0{str(descr)}\0{str(icon)}\0{str(number)}"
    if lookup not in _item_map:
        _item_map[lookup] = (id, name, descr, icon, number)
    return _item_map[lookup]


class AssetTask(PropertyGroup):
    """Keeps track of some progress needed for asset bridge"""
    __reg_order__ = 0

    name: StringProperty()

    start_time: FloatProperty(default=0)

    def set_cancelled(self, value):
        self["_cancelled"] = value

    # cancelled: property(lambda self: self.progress.cancelled)
    cancelled: BoolProperty(
        get=lambda self: self.progress.cancelled if self.progress else self.get("_cancelled", False),
        set=set_cancelled,
    )

    finished: BoolProperty()

    progress: Progress = property(
        lambda self: get_ab_settings(bpy.context).tasks_progress.get(self.name),
        lambda self, value: get_ab_settings(bpy.context).tasks_progress.update({self.name: value}),
    )

    def remove(self):
        tasks = get_ab_settings(bpy.context).tasks
        idx = list(tasks.values()).index(tasks[self.name])
        tasks.remove(idx)

    def cancel(self, remove: bool = True):
        """Cancel this task. This only marks the task a cancelled, and it is up to the script to interperet that.
        args:
            remove (bool): Whether to remove this task after cancelling."""
        self.cancelled = True
        self.finished = True
        if self.progress:
            self.progress.cancel()
        if remove:
            self.remove()

    def new_progress(self, max_steps: int) -> Progress:
        self.progress = Progress(max_steps, self, "progress_prop")
        return self.progress

    def update_progress(self, value: int, message: str = "") -> Progress:
        self.progress.progress = value
        if message:
            self.progress.message = message
        return self.progress

    def finish(self, remove: bool = True):
        if self.progress:
            self.progress.end()
        self.finished = True
        if remove:
            self.remove()

    def draw_progress(self, layout: UILayout, text: str = "", draw_cancel: bool = True):
        """Draw a progress bar for this task that draws either the progress message or the given text,
        and a cancel button, if draw_cancel enabled"""
        row = layout.row(align=True)
        row.prop(self, "ui_progress_prop", text=text or self.progress.message)
        if draw_cancel:
            row.scale_x = 1.25
            op = row.operator("asset_bridge.cancel_task", text="", icon="X")
            op.name = self.name
            op.bl_description = "Cancel task"


add_progress(AssetTask, "progress_prop")


def new_show_prop(name: str, default=True):
    return BoolProperty(name=name, description=f"Show {name} settings", default=default)


class AssetBridgeShowUISettings(PropertyGroup):
    """Properties for showing and hiding parts of the UI"""
    __reg_order__ = 0

    # HDRI
    hdri: new_show_prop("HDRI")

    hdri_coords: new_show_prop("Coordinates")

    hdri_color: new_show_prop("Color")

    # Material
    mat: new_show_prop("Material")

    mat_general: new_show_prop("General")

    mat_hsv: new_show_prop("Color")

    mat_mapping: new_show_prop("Mapping")

    mat_tiling: new_show_prop("Anti-Tiling")

    mat_displacement: new_show_prop("Displacement")


class AssetBridgeSettings(PropertyGroup):
    __reg_order__ = 1

    ui_show: PointerProperty(
        type=AssetBridgeShowUISettings,
        description="Properties for showing and hiding parts of the UI",
    )
    if TYPE_CHECKING:
        ui_show: AssetBridgeShowUISettings

    # TASKS
    # Tasks are a system for showing the progress of asset bridge processes dynamically in the UI
    # Each task has drawable properties that can be updated by other processes
    # and will be automatically updated in the UI
    tasks: CollectionProperty(type=AssetTask)
    if TYPE_CHECKING:
        tasks: OrderedDict[str, AssetTask]

    tasks_progress = {}

    def new_task(self, name: str = "") -> AssetTask:
        task = self.tasks.add()
        task.start_time = perf_counter()
        name = name or str(time_ns())
        task.name = name
        self.tasks_progress[name] = None
        return task

    prev_asset_name: StringProperty(default="NONE")

    @property
    def selected_asset(self):
        name = self.asset_idname
        if not name or name == "NONE":
            return None
        return get_asset_lists().all_assets[name]

    @property
    def asset_idname(self):
        context = bpy.context
        handle = context.asset_file_handle
        if handle:
            asset = handle.asset_data
            self.prev_asset_name = asset.description
            return asset.description
        elif self.prev_asset_name != "NONE":
            return self.prev_asset_name
        return "NONE"

    def asset_quality_items(self, context):
        asset_list_item = self.selected_asset
        if asset_list_item:
            items = []
            for i, level in enumerate(asset_list_item.ab_quality_levels):
                # Avoid enum bug
                icon = "CHECKMARK" if asset_list_item.is_downloaded(level[0]) else "IMPORT"
                items.append(_make_item(level[0], level[1], level[2], icon, i))
            return items
        return [("NONE", "None", "None")]

    def get_asset_quality(self):
        maximum = len(self.asset_quality_items(None))
        quality = self.get("_asset_quality", 0)
        return min(quality, maximum - 1)

    def set_asset_quality(self, value):
        self["_asset_quality"] = value

    asset_quality: EnumProperty(
        name="Quality",
        description="The quality level at which to download this asset",
        items=asset_quality_items,
        get=get_asset_quality,
        set=set_asset_quality,
    )

    reload_asset: BoolProperty(
        name="Re-Download asset",
        description="Re-Download this asset, instead of using the already downloaded version",
        default=False,
    )


class AssetBridgeIDSettings(PropertyGroup):
    """Used to identify whether a datablock has been imported by asset bridge"""

    # Used to tell with data blocks are dummies that should be replaced with downloaded assets
    is_dummy: BoolProperty()

    idname: StringProperty()

    quality_level: StringProperty()

    uuid: StringProperty(description="The identifier of this specific instance of the asset.\
        Used to determine if there are multiple objects as part of one asset after it has been imported.")

    index: IntProperty(description="The index of the imported asset,\
        used for swapping quality levels for models, as they can consist of multiple objects")

    # Used to tell if a datablock has been imported by asset bridge
    is_asset_bridge: BoolProperty()


class AssetBridgeMaterialSettings(AssetBridgeIDSettings, PropertyGroup):

    def enable_displacement_update(self, context: Context):
        self.id_data: Material
        nodes = self.id_data.node_tree.nodes
        for node in nodes:
            if node.type == "OUTPUT_MATERIAL":
                break
        else:
            return

        if links := node.inputs["Displacement"].links:
            link = links[0]
            link.is_muted = not self.enable_displacement
            link.from_node.mute = not self.enable_displacement
            # node.mute = not self.enable_displacement

    enable_displacement: BoolProperty(
        name="Enable material displacement",
        description="Enable displacement for this material in Cycles",
        default=False,
        update=enable_displacement_update,
    )


def get_ab_settings(context: bpy.types.Context) -> AssetBridgeSettings:
    """Get the global asset bridge settings, registered to `context.window_manager.asset_bridge`"""
    return context.window_manager.asset_bridge


def get_asset_settings(data_block: ID) -> AssetBridgeIDSettings:
    """Get the asset bridge settings for the given data block"""
    return data_block.asset_bridge


def register():
    bpy.types.WindowManager.asset_bridge = PointerProperty(type=AssetBridgeSettings)

    bpy.types.ID.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)
    # bpy.types.Object.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)
    # bpy.types.World.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)
    bpy.types.Material.asset_bridge = PointerProperty(type=AssetBridgeMaterialSettings)


def unregister():
    del bpy.types.WindowManager.asset_bridge

    # del bpy.types.Object.asset_bridge
    # del bpy.types.World.asset_bridge
    del bpy.types.Material.asset_bridge
