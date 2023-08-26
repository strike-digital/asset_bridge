import bpy
from bpy.props import StringProperty
from mathutils import Vector

from ..constants import NODES
from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_toggle_tiling_preview(BOperator.type):
    """Toggle a preview of the anti tiling effect, to make it easier to see the different segments"""

    material_name: StringProperty()

    def execute(self, context):
        material = bpy.data.materials[self.material_name]
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
