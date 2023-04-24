from bpy.types import Material
from mathutils import Vector

from ..constants import NODES
from ..helpers.btypes import FunctionToOperator

# @BOperator("asset_bridge"):
# class AB_OT_preview_tiling_node(Operator):

#     material_name =

#     def execute(self, context: Context):

#         return {"FINISHED"}


@FunctionToOperator("asset_bridge")
def preview_tiling_node(material: Material):
    nodes = material.node_tree.nodes
    if out_node := nodes.get(NODES.temp_output):
        nodes.remove(out_node)
        return

    tiling_node = nodes.get(NODES.anti_tiling)
    if tiling_node:
        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.name = NODES.temp_output
        out_node.label = NODES.temp_output
        out_node.location = tiling_node.location + Vector((0, 140))
        out_node.is_active_output = True
        material.node_tree.links.new(tiling_node.outputs[-1], out_node.inputs[0])