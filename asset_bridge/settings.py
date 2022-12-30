from typing import TYPE_CHECKING, OrderedDict
from bpy.types import PropertyGroup
from bpy.props import StringProperty, CollectionProperty, FloatProperty, BoolProperty, PointerProperty
from time import time_ns
import bpy

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


class AssetTask(PropertyGroup):
    """Keeps track of some progress needed for asset bridge"""
    __reg_order__ = 0

    name: StringProperty()

    progress: Progress = property(
        lambda self: get_ab_settings(bpy.context).tasks_progress.get(self.name),
        lambda self, value: get_ab_settings(bpy.context).tasks_progress.update({self.name: value}),
    )

    def new_progress(self, max_steps):
        self.progress = Progress(max_steps, self, "progress_prop")
        return self.progress

    def finish(self):
        if self.progress:
            self.progress.end()
        tasks = get_ab_settings(bpy.context).tasks
        idx = list(tasks.values()).index(tasks[self.name])
        tasks.remove(idx)


add_progress(AssetTask, "progress_prop")


class AssetBridgeSettings(PropertyGroup):
    __reg_order__ = 1

    tasks: CollectionProperty(type=AssetTask)
    if TYPE_CHECKING:
        tasks: OrderedDict[str, AssetTask]

    tasks_progress = {}

    def new_task(self, name: str = "") -> AssetTask:
        task = self.tasks.add()
        name = name or str(time_ns())
        task.name = name
        self.tasks_progress[name] = None
        return task


class AssetBridgeIDSettings(PropertyGroup):
    """Used to identify whether a datablock has been imported by asset bridge"""

    is_asset_bridge: BoolProperty()

    idname: StringProperty()


def get_ab_settings(context: bpy.types.Context) -> AssetBridgeSettings:
    """Get the global asset bridge settings, registered to `context.window_manager.asset_bridge`"""
    return context.window_manager.asset_bridge


def register():
    bpy.types.WindowManager.asset_bridge = PointerProperty(type=AssetBridgeSettings)

    bpy.types.Object.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)
    bpy.types.World.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)
    bpy.types.Material.asset_bridge = PointerProperty(type=AssetBridgeIDSettings)


def unregister():
    del bpy.types.WindowManager.asset_bridge

    del bpy.types.Object.asset_bridge
    del bpy.types.World.asset_bridge
    del bpy.types.Material.asset_bridge
    