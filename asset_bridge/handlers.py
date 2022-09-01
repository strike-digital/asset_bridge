from asset_bridge.operators import AB_OT_import_asset
import bpy
from bpy.app import handlers
from bpy.types import Scene
from mathutils import Vector as V


def get_asset_quality(scene):
    return scene.asset_bridge.browser.asset_quality


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
            handle = bpy.context.asset_file_handle
            if handle and handle.asset_data.description == name:
                return override["area"]
    else:
        if overrides:
            return overrides[0]["area"]
    return None


def get_active_region(mouse_pos):
    mouse_pos = V(mouse_pos)
    for area in bpy.context.screen.areas:
        print(mouse_pos, area.x, area.x + area.width)
        if (area.x < mouse_pos.x < area.x + area.width) and (area.y < mouse_pos.y < area.y + area.height):
            for region in area.regions:
                if region.type == "WINDOW":
                    return region
    else:
        return None


def is_link(area):
    return "LINK" in area.spaces.active.params.import_type


@handlers.persistent
def depsgraph_update_pre_handler(scene: Scene, _):
    """Check if an asset has been dragged from the asset browser"""
    quality = get_asset_quality(scene)
    # Hdris
    if (world := scene.world) and world.is_asset_bridge:
        name = world.asset_bridge_name
        bpy.data.worlds.remove(world)
        bpy.ops.asset_bridge.import_asset(
            "INVOKE_DEFAULT",
            asset_name=name,
            asset_quality=quality,
            link=is_link(get_browser_area(name)),
            from_asset_browser=True,
        )

    # Materials
    for obj in scene.objects:
        for slot in obj.material_slots:
            if (mat := slot.material) and mat.is_asset_bridge:
                name = mat.asset_bridge_name
                bpy.data.materials.remove(mat)
                # We can't pass a material slot directly, so set it as a class attribute.
                # This is very hacky, and there's almost certainly a good reason not to do it,
                # But I haven't found it yet ¯\_(ツ)_/¯
                AB_OT_import_asset.material_slot = slot
                bpy.ops.asset_bridge.import_asset(
                    "INVOKE_DEFAULT",
                    asset_name=name,
                    asset_quality=quality,
                    link=is_link(get_browser_area(name)),
                    from_asset_browser=True,
                )

    # Models
    objs = [o for o in scene.objects if o.is_asset_bridge]
    for obj in objs:
        name = obj.asset_bridge_name
        bpy.data.objects.remove(obj)
        bpy.ops.asset_bridge.import_asset(
            "INVOKE_DEFAULT",
            asset_name=name,
            at_mouse=True,
            link=is_link(get_browser_area(name)),
            asset_quality=quality,
            from_asset_browser=True,
        )

        continue


@handlers.persistent
def undo_post(scene, _):
    """If undo is called just after an asset has been imported, the asset will revert back to the original empty,
    which will be picked up by the depsgraph handler and have it's asset imported again,
    making it impossible to undo past that point.
    This prevents that by checking for any asset bridge empty and removing it
    before there is an update to the depsgraph"""
    # Hdris
    if (world := scene.world) and world.is_asset_bridge:
        bpy.data.worlds.remove(world)

    # Materials
    for obj in scene.objects:
        for slot in obj.material_slots:
            if (mat := slot.material) and mat.is_asset_bridge:
                bpy.data.materials.remove(mat)

    # Models
    obj_remove = []
    for obj in scene.objects:
        if obj.is_asset_bridge:
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