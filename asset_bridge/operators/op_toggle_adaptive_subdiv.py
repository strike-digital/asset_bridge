# import bpy
# from bpy.props import StringProperty
# from mathutils import Vector

# from ..constants import NODES
# from ..helpers.btypes import BOperator


# @BOperator("asset_bridge")
# class AB_OT_toggle_adaptive_subdiv(BOperator.type):
#     """Toggle adaptive subdivision on this object.

#     NOTE: This can be very expensive to calculate, and can slow down initialization of renders a lot,
#     as well as increasing memory usage substantially. It will provide the best looking displacement,
#     but be aware that it comes at a cost."""

#     material_name: StringProperty()

#     def execute(self, context):
#         material = bpy.data.materials[self.material_name]
#         nodes = material.node_tree.nodes
#         if out_node := nodes.get(NODES.temp_output):
#             nodes.remove(out_node)
#             return {"FINISHED"}

#         tiling_node = nodes.get(NODES.anti_tiling)
#         if tiling_node:
#             out_node = nodes.new("ShaderNodeOutputMaterial")
#             out_node.name = NODES.temp_output
#             out_node.label = NODES.temp_output
#             out_node.location = tiling_node.location + Vector((0, 140))
#             out_node.is_active_output = True
#             material.node_tree.links.new(tiling_node.outputs[-1], out_node.inputs[0])
#         return {"FINISHED"}
