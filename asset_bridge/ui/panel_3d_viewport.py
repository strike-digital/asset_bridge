from bpy.types import Node, Panel, Object, Material

from ..settings import get_ab_settings, get_asset_settings
from ..constants import NODES, NODE_GROUPS
from .ui_helpers import (DummyLayout, wrap_text, draw_inline_prop, draw_inline_column, draw_section_header,
                         draw_node_group_inputs)
from ..helpers.btypes import BPanel
from .menu_swap_asset import (AB_MT_swap_hdri_asset, AB_MT_swap_model_asset, AB_MT_swap_material_asset)


class Nodes():
    """A helper for storing important nodes in a material"""

    def __init__(self, all_nodes):
        pass

    def any(self):
        """Return whether any of the nodes exist"""
        for attr in self.__dict__.values():
            if attr and isinstance(attr, Node):
                return True
        return False


@BPanel(space_type="VIEW_3D", region_type="UI", category="Asset Bridge", label="Asset Settings")
class AB_PT_asset_props_viewport(Panel):
    bl_label = "Asset settings"

    can_draw = False

    @classmethod
    def poll(cls, context):
        cls.draw(cls, context)
        return cls.can_draw

    def draw(self, context):
        if hasattr(self, "layout"):
            layout = self.layout
            is_dummy = False
        else:
            layout = DummyLayout()
            is_dummy = True
        obj: Object = context.object
        show_props = get_ab_settings(context).ui_show
        FACTOR = .35
        PROP_SPACING = .4

        def draw_hdri_props():
            """
            DRAW HDRI SETTINGS
            """
            world = context.scene.world
            if not world:
                return False

            class HdriNodes(Nodes):
                __init__ = lambda self: None

                coords = world.node_tree.nodes.get(NODE_GROUPS.hdri_coords),
                color = world.node_tree.nodes.get(NODE_GROUPS.hdri_color),

            nodes = HdriNodes()

            if not nodes.any():
                return False
            elif is_dummy:
                return True

            column = layout.column(align=True)
            row = draw_section_header(
                column,
                "     HDRI Settings",
                show_props,
                "hdri",
                icon="WORLD",
                right_padding=4,
            )

            row = row.row()
            row.emboss = "PULLDOWN_MENU"
            row.menu(AB_MT_swap_hdri_asset.bl_idname, text="", icon="FILE_REFRESH")

            if not show_props.hdri:
                return True
            column = column.box().column(align=False)

            if node := nodes.color:
                col = column.column(align=True)
                draw_section_header(col, "Color", show_props, "hdri_color")
                if show_props.hdri_color:
                    box = col.box().column(align=True)
                    draw_node_group_inputs(node, box, context, False, spacing=PROP_SPACING, factor=FACTOR)

            if node := nodes.coords:
                col = column.column(align=True)
                draw_section_header(col, "Warping", show_props, "hdri_coords")
                if show_props.hdri_coords:
                    box = col.box().column(align=True)
                    draw_node_group_inputs(node, box, context, False, spacing=PROP_SPACING, factor=FACTOR)

        def draw_material_props():
            """
            DRAW MATERIAL SETTINGS
            """
            if not obj or len(obj.material_slots) == 0:
                return False

            class MatNodes(Nodes):
                """A helper for storing important nodes in a material"""

                def __init__(self, all_nodes):
                    self.tiling = all_nodes.get(NODES.anti_tiling)
                    self.mapping = all_nodes.get(NODES.mapping)
                    self.normal = all_nodes.get(NODES.normal_map)
                    self.scale = all_nodes.get(NODES.scale)
                    self.displacement = all_nodes.get(NODES.displacement)
                    self.displacement_scale = all_nodes.get(NODES.displacement_strength)
                    self.hsv = all_nodes.get(NODES.hsv)
                    self.roughness = all_nodes.get(NODES.roughness)
                    self.opacity = all_nodes.get(NODES.opacity)

            slot = obj.material_slots[obj.active_material_index]
            slots = [slot for slot in obj.material_slots if slot.material]
            mat: Material = slot.material
            if mat and mat.node_tree:
                nodes = MatNodes(mat.node_tree.nodes)

            for s in slots:
                if MatNodes(s.material.node_tree.nodes).any():
                    column = layout.column(align=True)
                    row = draw_section_header(
                        column,
                        "    Material Settings",
                        show_props,
                        "mat",
                        icon="MATERIAL",
                        right_padding=4,
                    )

                    row = row.row(align=True)
                    row.emboss = "PULLDOWN_MENU"
                    row.menu(AB_MT_swap_material_asset.bl_idname, text="", icon="FILE_REFRESH")
                    row.menu(AB_MT_swap_model_asset.bl_idname, text="", icon="FILE_REFRESH")

                    if not show_props.mat:
                        return True
                    column = column.box().column(align=False)
                    break
            else:
                return False

            if is_dummy:
                return True

            # MATERIAL SLOTS
            if len(obj.material_slots) > 1:
                column.template_list(
                    "MATERIAL_UL_matslots",
                    "",
                    obj,
                    "material_slots",
                    obj,
                    "active_material_index",
                    rows=1,
                )
                column.separator(factor=.1)

            column.template_ID(slot, "material")
            column.separator(factor=.1)

            if not mat or not nodes.any():
                return True

            principled_nodes = [n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"]

            # GENERAL
            if any([nodes.normal, nodes.scale, nodes.opacity, nodes.roughness]) or len(principled_nodes):
                col = column.column(align=True)
                draw_section_header(col, "General", show_props, "mat_general")
                if show_props.mat_general:
                    box = col.box().column(align=True)
                    render_engine = context.scene.render.engine
                    shading_type = context.space_data.shading.type
                    if nodes.opacity and (render_engine == "BLENDER_EEVEE" or shading_type == "MATERIAL"):
                        draw_inline_prop(box, mat, "blend_method", "Blend:", "", factor=FACTOR)
                        draw_inline_prop(box, mat, "shadow_method", "Shadow", "", factor=FACTOR)
                        box.separator(factor=PROP_SPACING)

                    if scale_node := nodes.scale:
                        socket = scale_node.outputs[0]
                        row = draw_inline_column(box, "Scale", factor=FACTOR).row(align=True)
                        row.prop(socket, "default_value", text="")
                        op = row.operator("asset_bridge.set_real_world_mat_scale", text="", icon="SHADING_BBOX")
                        op.object = obj.name
                        op.material = mat.name
                        box.separator(factor=PROP_SPACING)

                    if nor_node := nodes.normal:
                        socket = nor_node.inputs["Strength"]
                        draw_inline_prop(box, socket, "default_value", "Normal:", socket.name, factor=FACTOR)
                        box.separator(factor=PROP_SPACING)

                    if rough_math_node := nodes.roughness:
                        socket = rough_math_node.inputs[1]
                        draw_inline_prop(box, socket, "default_value", "Roughness:", "Amount", factor=FACTOR)
                        box.separator(factor=PROP_SPACING)
                    elif len(principled_nodes):
                        socket = principled_nodes[0].inputs["Roughness"]
                        if not socket.links:
                            draw_inline_prop(box, socket, "default_value", "Roughness:", "Amount", factor=FACTOR)
                            box.separator(factor=PROP_SPACING)

            # COLOR
            if hsv_node := nodes.hsv:
                col = column.column(align=True)
                draw_section_header(col, "Color", show_props, "mat_hsv")
                if show_props.mat_hsv:
                    box = draw_inline_column(col.box(), "HSV:", factor=FACTOR)
                    for socket in hsv_node.inputs[:-2]:
                        box.prop(socket, "default_value", text=socket.name)

            # MAPPING
            if mapping_node := nodes.mapping:
                col = column.column(align=True)
                draw_section_header(col, "Mapping", show_props, "mat_mapping")
                if show_props.mat_mapping:
                    box = col.box().column(align=True)
                    col = draw_inline_column(box, label="Location", factor=FACTOR)
                    socket = mapping_node.inputs["Location"]
                    col.prop(socket, "default_value", text="X", index=0)
                    col.prop(socket, "default_value", text="Y", index=1)
                    col.separator(factor=PROP_SPACING)

                    col = draw_inline_column(box, label="Scale", factor=FACTOR)
                    socket = mapping_node.inputs["Scale"]
                    col.prop(socket, "default_value", text="X", index=0)
                    col.prop(socket, "default_value", text="Y", index=1)
                    col.separator(factor=PROP_SPACING)

                    col = draw_inline_column(box, label="Rotation", factor=FACTOR)
                    socket = mapping_node.inputs["Rotation"]
                    col.prop(socket, "default_value", text="Z", index=2)
                    col.separator(factor=PROP_SPACING)

            # TILING
            if tiling_node := nodes.tiling:
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

                        draw_node_group_inputs(
                            tiling_node,
                            box,
                            context,
                            in_boxes=False,
                            spacing=PROP_SPACING,
                            factor=FACTOR,
                        )

            # DISPLACEMENT
            if (disp_node := nodes.displacement) and context.scene.render.engine == "CYCLES":
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
                        draw_inline_prop(
                            box,
                            disp_node.inputs["Midlevel"],
                            "default_value",
                            "Midlevel",
                            "",
                            factor=FACTOR,
                        )
                        if disp_scale_node := nodes.displacement_scale:
                            draw_inline_prop(
                                box,
                                disp_scale_node.inputs[0],
                                "default_value",
                                "Scale",
                                "",
                                factor=FACTOR,
                            )

                        # draw_inline_prop(box, disp_node.inputs["Scale"], "default_value", "Scale", "", factor=FACTOR)

            return nodes.any()

        drawn = any((draw_hdri_props(), draw_material_props()))

        self.can_draw = drawn
        return
        # return drawn

        if not drawn:
            box = layout.box().column(align=True)
            box.scale_y = .9
            wrap_text(context, "Select an imported Asset Bridge asset to see its settings here", box, centered=True)