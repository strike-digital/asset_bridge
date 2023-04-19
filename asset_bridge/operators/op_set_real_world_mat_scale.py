from statistics import mean

from bpy.types import Object, Material

from ..settings import get_asset_settings
from ..constants import NODES
from ..helpers.btypes import FunctionToOperator


@FunctionToOperator("asset_bridge", label="Set real world material scale")
def set_real_world_mat_scale(material: Material, object: Object):
    """Set the real world scale of an asset bridge material based on the dimensions of the provided object"""
    size = mean(object.dimensions)
    node = material.node_tree.nodes[NODES.scale]
    asset_list_item = get_asset_settings(material).asset_list_item
    node.outputs[0].default_value = size / asset_list_item.ab_material_size