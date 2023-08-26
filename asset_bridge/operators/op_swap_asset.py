import bpy
from bpy.props import StringProperty
from bpy.types import ID, Mesh, Curve, Object, NodeTree
from mathutils import Vector as V

from ..api import get_asset_lists
from ..settings import get_asset_settings
from ..helpers.assets import download_and_import_asset
from ..helpers.btypes import BOperator
from ..helpers.drawing import point_under_mouse
from ..apis.asset_utils import HDRI, MODEL, MATERIAL


def copy_nodes_settings(from_node_tree: NodeTree, to_node_tree: NodeTree):
    """Copy the input values and link mutings of every node from one tree to another"""
    nodes = from_node_tree.nodes
    for from_node in nodes:
        to_node = to_node_tree.nodes.get(from_node.name)
        if not to_node:
            continue
        if to_node.type == "VALUE":
            to_node.outputs[0].default_value = from_node.outputs[0].default_value
        for from_input, to_input in zip(from_node.inputs, to_node.inputs):
            if hasattr(to_input, "default_value"):
                to_input.default_value = from_input.default_value

            for from_link, to_link in zip(from_input.links, to_input.links):
                to_link.is_muted = from_link.is_muted


@BOperator("asset_bridge")
class AB_OT_swap_asset(BOperator.type):
    to_quality: StringProperty()

    asset_id: StringProperty(description="The identifier of the asset to be swapped")

    def execute(self, context):
        asset_list_item = get_asset_lists().all_assets[self.asset_id]
        asset = asset_list_item.to_asset(self.to_quality, "APPEND_REUSE")  # TODO: infer this automatically
        initial_obj: Object = context.object

        # Find 3D coordinates of the point under the mouse cursor
        if asset_list_item.ab_type == HDRI:
            region = context.region

            # Place in center of the viewport, taking the n panel into consideration
            npanel_width = 0
            for region in context.area.regions:
                if region.type == "UI":
                    npanel_width = region.width
            center = V(((region.width - npanel_width) / 2, region.height / 2))

            location = point_under_mouse(context, center, region=region)
            if location is None:
                # Couldn't find the location. The error is handled inside the function
                return self.CANCELLED
        else:
            location = initial_obj.location

        if asset_list_item.ab_type == MATERIAL:
            material_slot = initial_obj.material_slots[initial_obj.active_material_index]
        else:
            material_slot = None

        def clean_up_material(material, ignore_users=False):
            for node in material.node_tree.nodes:
                if not hasattr(node, "image") or not node.image:
                    continue
                if node.image.users == 1:
                    bpy.data.images.remove(node.image)
            if material.users == 0 or ignore_users:
                bpy.data.materials.remove(material)

        def on_completion(imported: ID):
            """Called whent the asset has been imported"""
            if asset_list_item.ab_type == HDRI:
                for world in list(bpy.data.worlds):
                    settings = get_asset_settings(world)
                    if settings.idname == asset_list_item.ab_idname and world != imported:
                        copy_nodes_settings(world.node_tree, imported.node_tree)
                        for node in world.node_tree.nodes:
                            if hasattr(node, "image") and (image := node.image):
                                if image.users == 1:
                                    bpy.data.images.remove(image)
                    if world.users == 0:
                        bpy.data.worlds.remove(world)
                imported.name = asset.import_name

            elif asset_list_item.ab_type == MATERIAL:
                for material in list(bpy.data.materials):
                    settings = get_asset_settings(material)
                    if settings.idname != asset_list_item.ab_idname or material == imported:
                        continue
                    copy_nodes_settings(material.node_tree, imported.node_tree)
                    clean_up_material(material)
                imported.name = asset.import_name

            elif asset_list_item.ab_type == MODEL:
                # Find all of the objects that are part of the old asset, and remove all of their data.
                done = set()
                to_remove = []
                for obj in list(bpy.data.objects):
                    settings = get_asset_settings(obj)
                    if any(
                        (
                            not settings.is_asset_bridge,
                            settings.uuid in done,
                            settings.uuid != get_asset_settings(initial_obj).uuid,
                        )
                    ):
                        continue

                    # Get a list of all objects in the model asset
                    asset_objs: list[Object] = []
                    for obj2 in list(bpy.data.objects):
                        settings2 = get_asset_settings(obj2)
                        if settings2.uuid == settings.uuid:
                            asset_objs.append(obj2)

                    # Copy the transfroms
                    # This relies on the objects iterating in the same order as when they were first imported,
                    # and has the potential to go wrong at some point.
                    # TODO: Come up with something better
                    for i, new_asset_obj in enumerate(imported.objects):
                        for old_asset_obj in asset_objs:
                            if get_asset_settings(old_asset_obj).index == i:
                                new_asset_obj.location = old_asset_obj.location
                                new_asset_obj.rotation_euler = old_asset_obj.rotation_euler
                                new_asset_obj.scale = old_asset_obj.scale

                    # Remove the object if that is the only user.
                    for asset_obj in asset_objs:
                        for slot in asset_obj.material_slots:
                            if slot.material and slot.material.use_nodes:
                                clean_up_material(slot.material, ignore_users=True)
                        if asset_obj.data and asset_obj.data.users == 1:
                            to_remove.append(asset_obj.data)
                        elif asset_obj.type == "EMPTY":
                            to_remove.append(asset_obj)

                    done.add(settings.uuid)

                for item in to_remove:
                    if isinstance(item, Mesh):
                        bpy.data.meshes.remove(item)
                    elif isinstance(item, Curve):
                        bpy.data.curves.remove(item)
                    elif isinstance(item, Object):
                        bpy.data.objects.remove(item)

                for collection in list(bpy.data.collections):
                    settings = get_asset_settings(collection)
                    if settings.idname != asset_list_item.ab_idname or collection == imported:
                        continue
                    if collection.users == 1:
                        bpy.data.collections.remove(collection)

        download_and_import_asset(
            context,
            asset,
            material_slot,
            draw=True,
            location=location,
            on_completion=on_completion,
        )
