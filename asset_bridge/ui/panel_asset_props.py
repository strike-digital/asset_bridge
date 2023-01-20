from ..settings import get_ab_settings, get_asset_settings
from ..helpers.ui import draw_inline_column, draw_inline_prop, draw_node_group_inputs, wrap_text
from ..constants import NODE_GROUPS, NODES
from ..btypes import BPanel
from bpy.types import Material, Node, Object, Panel, UILayout


class AssetPropsPanel(Panel):
    __no_reg__ = True
    bl_label = "Asset settings"

    def draw(self, context):
        layout = self.layout
        obj: Object = context.object
        show_props = get_ab_settings(context).ui_show

        def draw_section_header(
            layout: UILayout,
            name: str,
            hide_prop_data=None,
            hide_prop_name=None,
            centered: bool = True,
            show_icon: bool = True,
            icon: str = "",
            right_padding: int = 6,
        ):
            box = layout.box()
            row = box.row(align=True)
            if hide_prop_data:
                if show_icon:
                    arrow_icon = "TRIA_RIGHT" if not getattr(hide_prop_data, hide_prop_name) else "TRIA_DOWN"
                    icon = icon or arrow_icon
                    name += " " * right_padding
                else:
                    icon = "NONE"
                    row.active = not getattr(hide_prop_data, hide_prop_name)
                row.prop(hide_prop_data, hide_prop_name, text=name, emboss=False, icon=icon)
            else:
                if centered:
                    row.alignment = "CENTER"
                icon = icon or "NONE"
                row.label(text=name, icon=icon)

        def draw_hdri_props():
            world = context.scene.world
            if not world:
                return False

            nodes = {
                "coords": world.node_tree.nodes.get(NODE_GROUPS.hdri_coords),
                "color": world.node_tree.nodes.get(NODE_GROUPS.hdri_color),
            }

            if not any(nodes.values()):
                return False

            column = layout.column(align=True)
            draw_section_header(
                column,
                "HDRI Settings",
                show_props,
                "hdri",
                icon="WORLD",
                right_padding=4,
            )
            if not show_props.hdri:
                return True
            column = column.box().column(align=False)

            if node := nodes["color"]:
                col = column.column(align=True)
                draw_section_header(col, "Color", show_props, "hdri_color")
                if show_props.hdri_color:
                    box = col.box().column(align=True)
                    draw_node_group_inputs(node, box, context, False)

            if node := nodes["coords"]:
                col = column.column(align=True)
                draw_section_header(col, "Warping", show_props, "hdri_coords")
                if show_props.hdri_coords:
                    box = col.box().column(align=True)
                    draw_node_group_inputs(node, box, context, False)

        def draw_material_props():
            if not obj and len(obj.material_slots) > 0:
                return False

            def get_material_nodes(all_nodes: list[Node]):
                nodes = {"tiling": None, "mapping": None, "normal": None, "scale": None, "displacement": None}
                nodes["tiling"] = all_nodes.get(NODES.anti_tiling)
                nodes["mapping"] = all_nodes.get(NODES.mapping)
                nodes["normal"] = all_nodes.get(NODES.normal_map)
                nodes["scale"] = all_nodes.get(NODES.scale)
                nodes["displacement"] = all_nodes.get(NODES.displacement)
                nodes["displacement_scale"] = all_nodes.get(NODES.displacement_strength)
                return nodes

            slot = obj.material_slots[obj.active_material_index]
            slots = [slot for slot in obj.material_slots if slot.material]
            mat: Material = slot.material
            if mat:
                nodes = get_material_nodes(mat.node_tree.nodes)

            for slot in slots:
                if any(get_material_nodes(slot.material.node_tree.nodes).values()):
                    column = layout.column(align=True)
                    draw_section_header(
                        column,
                        "Material Settings",
                        show_props,
                        "mat",
                        icon="MATERIAL",
                        right_padding=4,
                    )
                    if not show_props.mat:
                        return True
                    column = column.box().column(align=False)
                    break
            else:
                return False

            if len([slot for slot in obj.material_slots if slot.material]) > 1:
                column.template_list(
                    "MATERIAL_UL_matslots",
                    "",
                    obj,
                    "material_slots",
                    obj,
                    "active_material_index",
                    rows=1,
                )

            if not any(nodes.values()):
                return True

            if any([nodes["normal"], nodes["scale"]]):
                col = column.column(align=True)
                draw_section_header(col, "General", show_props, "mat_general")
                if show_props.mat_general:
                    box = col.box().column(align=True)
                    if scale_node := nodes["scale"]:
                        socket = scale_node.outputs[0]
                        draw_inline_prop(box, socket, "default_value", "Scale", "")
                        box.separator()

                    if nor_node := nodes["normal"]:
                        socket = nor_node.inputs["Strength"]
                        draw_inline_prop(box, socket, "default_value", "Normal:", socket.name)
                        box.separator()

            if mapping_node := nodes["mapping"]:
                col = column.column(align=True)
                draw_section_header(col, "Mapping", show_props, "mat_mapping")
                if show_props.mat_mapping:
                    box = col.box().column(align=True)
                    col = draw_inline_column(box, label="Location")
                    socket = mapping_node.inputs["Location"]
                    col.prop(socket, "default_value", text="X", index=0)
                    col.prop(socket, "default_value", text="Y", index=1)
                    col.separator()

                    col = draw_inline_column(box, label="Rotation")
                    socket = mapping_node.inputs["Rotation"]
                    col.prop(socket, "default_value", text="Z", index=2)
                    col.separator()

                    col = draw_inline_column(box, label="Scale")
                    socket = mapping_node.inputs["Scale"]
                    col.prop(socket, "default_value", text="X", index=0)
                    col.prop(socket, "default_value", text="Y", index=1)
                    col.separator()

            if tiling_node := nodes["tiling"]:
                col = column.column(align=True)
                draw_section_header(col, "Anti-Tiling", show_props, "mat_tiling")
                if show_props.mat_tiling:
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

                        draw_node_group_inputs(tiling_node, box, context, in_boxes=False)

            if (disp_node := nodes["displacement"]) and context.scene.render.engine == "CYCLES":
                col = column.column(align=True)
                draw_section_header(col, "Displacement", show_props, "mat_displacement")
                if show_props.mat_displacement and disp_node.outputs[0].links:
                    box = col.box().column(align=True)
                    settings = get_asset_settings(mat)
                    box.prop(
                        settings,
                        "enable_displacement",
                        text="Disable" if settings.enable_displacement else "Enable",
                        toggle=True,
                    )
                    if settings.enable_displacement:
                        box.separator()
                        box = box.column(align=True)
                        draw_inline_prop(box, disp_node.inputs["Midlevel"], "default_value", "Midlevel", "")
                        if disp_scale_node := nodes["displacement_scale"]:
                            draw_inline_prop(box, disp_scale_node.inputs[0], "default_value", "Scale", "")

                        # draw_inline_prop(box, disp_node.inputs["Scale"], "default_value", "Scale", "")

            return any(nodes.values())

        drawn = any((draw_hdri_props(), draw_material_props()))

        if not drawn:
            box = layout.box().column(align=True)
            box.scale_y = .9
            wrap_text(context, "Select an imported Asset Bridge asset to see its settings here", box, centered=True)


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
