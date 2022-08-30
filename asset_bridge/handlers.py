import bpy
from bpy.app import handlers
from bpy.types import Scene
from .assets import Asset
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_origin_3d


@handlers.persistent
def depsgraph_update_pre_handler(scene: Scene, _):
    """Check if an asset has been dragged from the asset browser"""

    # Hdris
    if (world := scene.world) and world.is_asset_bridge:
        asset = Asset(world.asset_bridge_name)
        asset.import_asset(bpy.context, link=False)
        bpy.data.worlds.remove(world)

    # Materials
    for obj in scene.objects:
        for slot in obj.material_slots:
            if (mat := slot.material) and mat.is_asset_bridge:
                asset = Asset(mat.asset_bridge_name)
                asset.import_asset(bpy.context, material_slot=slot)
                bpy.data.materials.remove(mat)

    # Models
    obj_remove = []
    obj_assets: list[Asset] = []
    for obj in scene.objects:
        if obj.is_asset_bridge:
            obj_remove.append(obj)
            obj_assets.append(Asset(obj.asset_bridge_name))

    for obj in obj_remove:
        bpy.data.objects.remove(obj)

    for asset in obj_assets:
        # asset.download_asset(bpy.context)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        region = bpy.context.region
        r3d = region.data
        coord = (region.width / 2, region.height / 2)

        ab = scene.asset_bridge
        bpy.ops.asset_bridge.get_mouse_pos("INVOKE_DEFAULT")
        coord = ab.mouse_pos
        view_vector = region_2d_to_vector_3d(region, r3d, coord)
        ray_origin = region_2d_to_origin_3d(region, r3d, coord)

        result = scene.ray_cast(depsgraph, ray_origin, view_vector)

        asset.import_asset(bpy.context, link=False, location=result[1])


def register():
    handlers.depsgraph_update_pre.append(depsgraph_update_pre_handler)


def unregister():
    for handler in handlers.depsgraph_update_pre:
        if handler.__name__ == depsgraph_update_pre_handler.__name__:
            handlers.depsgraph_update_pre.remove(handler)