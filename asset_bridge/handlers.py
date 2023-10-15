# from asset_bridge.operators import AB_OT_import_asset
from .helpers.compatibility import get_active_asset
from .helpers.btypes import ExecContext
from .constants import ASSET_LIB_NAME
import bpy
from bpy.app import handlers
from bpy.types import Scene

from .settings import get_ab_settings
from .operators.op_import_asset import AB_OT_import_asset


def get_asset_quality(context):
    return get_ab_settings(context).asset_quality


def get_browser_area(name) -> bpy.types.Area:
    """Find the area that has the correct asset selected in the asset browser.
    If not found returns None. This isn't perfect as if you have to asset browsers selecting the same asset,
    it will just select the first one"""
    overrides = []
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "FILE_BROWSER" and area.ui_type == "ASSETS":
                overrides.append({"window": window, "area": area})
    for override in overrides:
        with bpy.context.temp_override(**override):
            handle = get_active_asset(bpy.context)
            if handle and handle.asset_data.description == name:
                return override["area"]
    else:
        if overrides:
            return overrides[0]["area"]
    return None


def link_method(area):
    import_type = area.spaces.active.params.import_type
    if import_type == "FOLLOW_PREFS":
        lib = bpy.context.preferences.filepaths.asset_libraries.get(ASSET_LIB_NAME)
        import_type = lib.import_method if lib else "APPED_REUSE"
    return import_type


prev_materials = {}
prev_world = None


@handlers.persistent
def depsgraph_update_pre_handler(scene: Scene, _):
    """Check if an asset has been dragged from the asset browser"""

    if bpy.app.background:
        return

    quality = get_asset_quality(bpy.context)
    reload = bpy.context.window_manager.asset_bridge.reload_asset

    # Hdris
    global prev_world
    if (world := scene.world) and world.asset_bridge.is_dummy:
        name = world.asset_bridge.idname
        bpy.data.worlds.remove(world)
        # print("World!", name)
        AB_OT_import_asset.run(
            ExecContext.INVOKE,
            asset_name=name,
            asset_quality=quality,
            link_method=link_method(get_browser_area(name)),
            reload=reload,
            at_mouse=True,
        )
        scene.world = prev_world

    prev_world = scene.world or prev_world

    # Materials
    global prev_materials
    for obj in scene.objects:
        for i, slot in enumerate(obj.material_slots):
            if (mat := slot.material) and mat.asset_bridge.is_dummy:
                name = mat.asset_bridge.idname
                bpy.data.materials.remove(mat)
                # print("Material!", name)
                # We can't pass a material slot directly, so set it as a class attribute.
                # This is very hacky, and there's almost certainly a good reason not to do it,
                # But I haven't found it yet ¯\_(ツ)_/¯
                AB_OT_import_asset.run(
                    ExecContext.INVOKE,
                    asset_name=name,
                    at_mouse=True,
                    # location=bpy.context.object.location,
                    asset_quality=quality,
                    link_method=link_method(get_browser_area(name)),
                    reload=reload,
                    material_slot=slot,
                )
                try:
                    slot.material = prev_materials[obj.name][i]
                except (IndexError, KeyError) as e:
                    print(e)
                    continue
                except ReferenceError:
                    continue

    for obj in bpy.data.objects:
        mats = [slot.material for slot in obj.material_slots]
        for i, mat in enumerate(mats):
            prev_mats = prev_materials.get(obj.name)
            if not prev_mats or len(prev_mats) != len(mats):
                continue

            if not mat:
                mats[i] = prev_mats[i]

        prev_materials[obj.name] = mats

    # Models
    objs = [o for o in scene.objects if o.asset_bridge.is_dummy]
    for obj in objs:
        name = obj.asset_bridge.idname
        bpy.data.objects.remove(obj)
        # print("Object!", name)
        AB_OT_import_asset.run(
            ExecContext.INVOKE,
            asset_name=name,
            link_method=link_method(get_browser_area(name)),
            at_mouse=True,
            asset_quality=quality,
            reload=reload,
        )


@handlers.persistent
def undo_post(scene, _):
    """If undo is called just after an asset has been imported, the asset will revert back to the original empty,
    which will be picked up by the depsgraph handler and have it's asset imported again,
    making it impossible to undo past that point.
    This prevents that by checking for any asset bridge empty and removing it
    before there is an update to the depsgraph"""
    # Hdris
    if (world := scene.world) and world.asset_bridge.is_dummy:
        bpy.data.worlds.remove(world)

    # Materials
    for obj in scene.objects:
        for slot in obj.material_slots:
            if (mat := slot.material) and mat.asset_bridge.is_dummy:
                bpy.data.materials.remove(mat)

    # Models
    obj_remove = []
    for obj in scene.objects:
        if obj.asset_bridge.is_dummy:
            obj_remove.append(obj)

    for obj in obj_remove:
        bpy.data.objects.remove(obj)


def register():
    handlers.depsgraph_update_pre.append(depsgraph_update_pre_handler)
    handlers.undo_post.append(undo_post)


def unregister():
    for handler in list(handlers.depsgraph_update_pre):
        if handler.__name__ == depsgraph_update_pre_handler.__name__:
            handlers.depsgraph_update_pre.remove(handler)
    for handler in list(handlers.undo_post):
        if handler.__name__ == undo_post.__name__:
            handlers.undo_post.remove(handler)

    global prev_materials
    global prev_world
    prev_materials = {}
    prev_world = None
