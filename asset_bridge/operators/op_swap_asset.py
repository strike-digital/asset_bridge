import bpy
from bpy.props import StringProperty
from bpy.types import ID, Object, Operator
from mathutils import Vector as V

from ..api import get_asset_lists
from ..settings import get_asset_settings
from ..helpers.assets import download_and_import_asset
from ..helpers.btypes import BOperator
from ..helpers.drawing import point_under_mouse
from ..apis.asset_utils import HDRI, MATERIAL


@BOperator("asset_bridge")
class AB_OT_swap_asset(Operator):

    to_quality: StringProperty()

    asset_id: StringProperty(description="The identifier of the asset to be swapped")

    def execute(self, context):

        asset_list_item = get_asset_lists().all_assets[self.asset_id]
        asset = asset_list_item.to_asset(self.to_quality, "APPEND_REUSE")  # TODO: infer this automatically
        obj: Object = context.object

        # Find 3D coordinates of the point under the mouse cursor
        if asset_list_item.type == HDRI:
            region = context.region
            center = V((region.width / 2, region.height / 2))
            location = point_under_mouse(context, center, region=region)
            if location is None:
                # Couldn't find the location. The error is handled inside the function
                return {"CANCELLED"}
        else:
            location = obj.location

        if asset_list_item.type == MATERIAL:
            material_slot = obj.material_slots[obj.active_material_index]
        else:
            material_slot = None

        def on_completion(imported: ID):
            """Called whent the asset has been imported"""
            if asset_list_item.type == HDRI:
                for world in list(bpy.data.worlds):
                    settings = get_asset_settings(world)
                    if settings.idname == asset_list_item.idname:
                        for node in world.node_tree.nodes:
                            if hasattr(node, "image") and (image := node.image):
                                if image.users == 0:
                                    bpy.data.images.remove(image)
                    if world.users == 0:
                        bpy.data.worlds.remove(world)
                imported.name = asset.import_name

            elif asset_list_item.type == MATERIAL:
                for material in list(bpy.data.materials):
                    settings = get_asset_settings(material)
                    if settings.idname != asset_list_item.idname:
                        continue
                    for node in material.node_tree.nodes:
                        if not hasattr(node, "image") or not node.image:
                            continue
                        if node.image.users == 0:
                            bpy.data.images.remove(node.image)
                    if material.users == 0:
                        bpy.data.materials.remove(material)
                imported.name = asset.import_name

        download_and_import_asset(
            context,
            asset,
            material_slot,
            draw=True,
            location=location,
            on_completion=on_completion,
        )
        return {"FINISHED"}
