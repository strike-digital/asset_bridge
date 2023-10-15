# from __future__ import annotations
from time import perf_counter, time_ns
from typing import TYPE_CHECKING, OrderedDict

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import ID, Collection, Context, Material, PropertyGroup, UILayout

from .api import get_asset_lists
from .helpers.compatibility import get_active_asset, get_asset_metadata
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

    # Import settings
    import_mat: new_show_prop("Material")

    import_model: new_show_prop("Model")


class AssetBridgeWmSettings(PropertyGroup):
    """General settings that can be kept in the window manager.
    This means that they get reset when starting a new blender session,
    but otherwise they are more global than scene settings."""

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
        return get_asset_lists().all_assets.get(name, None)
        return get_asset_lists().all_assets[name]

    @property
    def asset_idname(self) -> str:
        context = bpy.context
        handle = get_active_asset(context)
        if handle:
            metadata = get_asset_metadata(handle)
            self.prev_asset_name = metadata.description
            return metadata.description
        elif self.prev_asset_name != "NONE":
            return self.prev_asset_name
        return "NONE"

    def asset_quality_items(self, context) -> list[tuple[str]]:
        asset_list_item = self.selected_asset
        if asset_list_item:
            items = []
            for i, level in enumerate(asset_list_item.ab_quality_levels):
                name, label, description = level
                icon = "CHECKMARK" if asset_list_item.is_downloaded(level[0]) else "IMPORT"

                # If no name is found, should only happen due to a difficult asset.
                if not name:
                    name = "NONE"
                    label = "No quality level..."
                    description = "This asset has no quality level available, please contact me about this :)"
                    icon = "X"

                # Avoid enum bug
                items.append(_make_item(name, label, description, icon, i))
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


class AssetBridgeSceneSettings(PropertyGroup):
    """General settings that need to be kept per-scene"""

    apply_real_world_scale: BoolProperty(
        name="Use real world scale",
        default=False,
        description="Set the scale of the imported material to be accurate to a real world scale when imported.\n\n\
        This only applies to materials that have their dimensions defined, otherwise the texture dimension \
        will be assumed to be 1m x 1m (the same as if the setting wasn't enabled)".replace(
            "  ", ""
        ),
    )

    import_collection: PointerProperty(
        type=Collection,
        name="Default import collection",
        description="The collection in which to place newly imported models.\n\
        If left blank, this will default to currently active collection.".replace(
            "  ", ""
        ),
    )


class AssetBridgeIDSettings(PropertyGroup):
    """Used to identify whether a datablock has been imported by asset bridge"""

    # Used to tell with data blocks are dummies that should be replaced with downloaded assets
    is_dummy: BoolProperty()

    idname: StringProperty()

    quality_level: StringProperty()

    uuid: StringProperty(
        description="The identifier of this specific instance of the asset.\
        Used to determine if there are multiple objects as part of one asset after it has been imported."
    )

    index: IntProperty(
        description="The index of the imported asset,\
        used for swapping quality levels for models, as they can consist of multiple objects"
    )

    # Used to tell if a datablock has been imported by asset bridge
    is_asset_bridge: BoolProperty()

    version: FloatVectorProperty(
        name="Asset Version",
        description="The version number of this asset. The order is (Breaking, Important, Minor).\
        Used for versioning in the addon.",
        size=3,
    )

    @property
    def asset_list_item(self):
        return get_asset_lists().all_assets[self.idname]


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


def get_ab_settings(context: bpy.types.Context) -> AssetBridgeWmSettings:
    """Get the global asset bridge settings, registered to `context.window_manager.asset_bridge`"""
    return context.window_manager.asset_bridge


def get_ab_scene_settings(context: bpy.types.Context) -> AssetBridgeSceneSettings:
    """Get the scene specific asset bridge settings, registered to `context.scene.asset_bridge`"""
    return context.scene.asset_bridge


def get_asset_settings(data_block: ID) -> AssetBridgeIDSettings:
    """Get the asset bridge settings for the given data block"""
    return data_block.asset_bridge


def register():
    bpy.types.WindowManager.asset_bridge = PointerProperty(type=AssetBridgeWmSettings)
    bpy.types.Scene.asset_bridge = PointerProperty(type=AssetBridgeSceneSettings)
    bpy.types.ID.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)
    bpy.types.Material.asset_bridge = PointerProperty(type=AssetBridgeMaterialSettings)


def unregister():
    del bpy.types.WindowManager.asset_bridge
    del bpy.types.Scene.asset_bridge
    del bpy.types.ID.asset_bridge
    del bpy.types.Material.asset_bridge
