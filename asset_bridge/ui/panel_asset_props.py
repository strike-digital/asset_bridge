from ..helpers.ui import draw_inline_prop, draw_node_group_inputs, wrap_text
from ..constants import NODE_NAMES
from ..btypes import BPanel
from bpy.types import Node, NodeSocket, Object, Panel, UILayout


class AssetPropsPanel(Panel):
    __no_reg__ = True
    bl_label = "Asset settings"

    def draw(self, context):
        layout = self.layout
        obj: Object = context.object

        def draw_section_header(layout: UILayout, name: str, centered: bool = True):
            box = layout.box()
            row = box.row(align=True)
            if centered:
                row.alignment = "CENTER"
            row.label(text=name)

        def draw_material_props():
            tiling_node = mapping_node = normal_node = None
            is_drawn = False
            column = layout.column(align=True)
            draw_section_header(column, "Material Settings")
            column = column.box().column(align=False)
            for slot in obj.material_slots:
                mat = slot.material
                if not mat:
                    continue

                for node in mat.node_tree.nodes:
                    node: Node
                    if node.name == NODE_NAMES.anti_tiling:
                        tiling_node = node
                    elif node.name == NODE_NAMES.mapping:
                        mapping_node = node
                    elif node.name == NODE_NAMES.normal_map:
                        normal_node = node

            if normal_node:
                col = column.column(align=True)
                draw_section_header(col, "General")
                box = col.box().column(align=True)

                socket = normal_node.inputs["Strength"]
                draw_inline_prop(box, socket, "default_value", "Normal:", socket.name)

            if mapping_node:
                column.separator(factor=.5)
                col = column.column(align=True)
                draw_section_header(col, "Mapping")
                box = col.box().column(align=True)
                for i, socket in enumerate(mapping_node.inputs):
                    if socket.links:
                        continue
                    draw_inline_prop(box, socket, "default_value", socket.name, "")

                    if i < len(mapping_node.inputs) - 1:
                        box.separator()

            if tiling_node:
                column.separator(factor=.5)
                col = column.column(align=True)
                draw_section_header(col, "Anti-Tiling")
                box = col.box().column(align=True)

                box.prop(
                    tiling_node,
                    "mute",
                    text="Enable" if tiling_node.mute else "Disable",
                    toggle=True,
                    invert_checkbox=True,
                )
                if not tiling_node.mute:
                    box.separator()
                    box = box.column(align=True)
                    box.active = not tiling_node.mute

                    draw_node_group_inputs(tiling_node, box, context, in_boxes=False)
                is_drawn = True
            return is_drawn

        drawn = draw_material_props()

        if not drawn:
            box = layout.box().column(align=True)
            box.scale_y = .9
            wrap_text(context, "Select an imported Asset Bridge asset to see its settings here", box, centered=True)

    # @classmethod
    # def prop_panel_poll(cls)


# @BPanel(space_type="FILE_BROWSER", region_type="TOOLS", index=100, show_header=False)
# class AB_PT_asset_props_browser(AssetPropsPanel, AssetBrowserPanel):
#     __no_reg__ = False

#     __reg_order__ = 100

#     @classmethod
#     def poll(cls, context):
#         if context.area.ui_type != "ASSETS":
#             return False
#         if ASSET_LIB_NAME != context.area.spaces.active.params.asset_library_ref:
#             return False
#         return cls.asset_browser_panel_poll(context)


@BPanel(space_type="VIEW_3D", region_type="UI", category="Asset Bridge", label="Asset Settings")
class AB_PT_asset_props_viewport(AssetPropsPanel):
    __no_reg__ = False
