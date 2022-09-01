from asset_bridge.operators import AB_OT_import_asset
import bpy
from bpy.app import handlers
from bpy.types import Scene
from .assets import Asset
from mathutils import Vector as V
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_origin_3d


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
    print(list(t.type for t in bpy.context.screen.areas))
    print(bpy.context.window.screen.areas[0].type)
    # for window in bpy.context.


def is_link(area):
    return "LINK" in area.spaces.active.params.import_type


@handlers.persistent
def depsgraph_update_pre_handler(scene: Scene, _):
    """Check if an asset has been dragged from the asset browser"""
    quality = get_asset_quality(scene)
    # Hdris
    if (world := scene.world) and world.is_asset_bridge:
        area = get_browser_area(name=world.asset_bridge_name)
        asset = Asset(world.asset_bridge_name)
        asset.import_asset(bpy.context, link=is_link(area), quality=quality)
        bpy.data.worlds.remove(world)

    # Materials
    for obj in scene.objects:
        for slot in obj.material_slots:
            if (mat := slot.material) and mat.is_asset_bridge:
                name = mat.asset_bridge_name
                bpy.ops.asset_bridge.import_asset(
                    "INVOKE_DEFAULT",
                    asset_name=name,
                    asset_quality=quality,
                    link=is_link(get_browser_area(name)),
                )
                # asset = Asset(mat.asset_bridge_name)
                # area = get_browser_area(name=mat.asset_bridge_name)
                # asset.import_asset(bpy.context, link=is_link(area), material_slot=slot, quality=quality)
                bpy.data.materials.remove(mat)

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
        )

        continue
        # ("INVOKE_DEFAULT", )
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bpy.ops.asset_bridge.get_mouse_pos("INVOKE_DEFAULT")
        ab = scene.asset_bridge
        coord = ab.mouse_pos
        region = get_active_region(ab.mouse_pos)
        r3d = region.data
        bpy.ops.asset_bridge.get_mouse_pos("INVOKE_DEFAULT", region=True)
        # coord = (region.width / 2, region.height / 2)
        coord = ab.mouse_pos

        view_vector = region_2d_to_vector_3d(region, r3d, coord)
        ray_origin = region_2d_to_origin_3d(region, r3d, coord)

        result = scene.ray_cast(depsgraph, ray_origin, view_vector)

        area = get_browser_area(name=asset.name)
        asset.import_asset(bpy.context, link=is_link(area), location=result[1], quality=quality)


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