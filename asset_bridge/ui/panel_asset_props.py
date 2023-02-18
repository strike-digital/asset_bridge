from bpy.types import Node, Panel, Object, Material, UILayout

from ..settings import get_ab_settings, get_asset_settings
from ..constants import NODES, NODE_GROUPS
from .ui_helpers import (wrap_text, draw_inline_prop, draw_inline_column, draw_node_group_inputs)
from ..helpers.btypes import BPanel
from .menu_swap_asset import (AB_MT_swap_hdri_asset, AB_MT_swap_model_asset, AB_MT_swap_material_asset)


class DummyLayout():
    """An immitator of the blender UILayout class, used so that the draw function can be run as a poll function"""

    def row(*args, **kwargs):
        return DummyLayout()

    def box(*args, **kwargs):
        return DummyLayout()

    def column(*args, **kwargs):
        return DummyLayout()

    def split(*args, **kwargs):
        return DummyLayout()

    def label(*args, **kwargs):
        return DummyLayout()

    def prop(*args, **kwargs):
        return DummyLayout()

    def menu(*args, **kwargs):
        return DummyLayout()


class AssetPropsPanel(Panel):
    __no_reg__ = True
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
            return row

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
            row.menu(AB_MT_swap_hdri_asset.bl_idname, text="", icon="IMPORT")

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
            if not obj or len(obj.material_slots) == 0:
                return False

            def get_material_nodes(all_nodes: list[Node]):
                nodes = {}
                nodes["tiling"] = all_nodes.get(NODES.anti_tiling)
                nodes["mapping"] = all_nodes.get(NODES.mapping)
                nodes["normal"] = all_nodes.get(NODES.normal_map)
                nodes["scale"] = all_nodes.get(NODES.scale)
                nodes["displacement"] = all_nodes.get(NODES.displacement)
                nodes["displacement_scale"] = all_nodes.get(NODES.displacement_strength)
                nodes["hsv"] = all_nodes.get(NODES.hsv)
                nodes["rough_gamma"] = all_nodes.get(NODES.rough_gamma)
                return nodes

            slot = obj.material_slots[obj.active_material_index]
            slots = [slot for slot in obj.material_slots if slot.material]
            mat: Material = slot.material
            if mat:
                nodes = get_material_nodes(mat.node_tree.nodes)

            for s in slots:
                if any(get_material_nodes(s.material.node_tree.nodes).values()):
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
                    row.menu(AB_MT_swap_material_asset.bl_idname, text="", icon="IMPORT")
                    row.menu(AB_MT_swap_model_asset.bl_idname, text="", icon="IMPORT")

                    if not show_props.mat:
                        return True
                    column = column.box().column(align=False)
                    break
            else:
                return False

            if is_dummy:
                return True

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

            if not mat or not any(nodes.values()):
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

                    if rough_gamma_node := nodes["rough_gamma"]:
                        socket = rough_gamma_node.inputs[1]
                        draw_inline_prop(box, socket, "default_value", "Roughness:", "Amount")
                        box.separator()

            if hsv_node := nodes["hsv"]:
                col = column.column(align=True)
                draw_section_header(col, "Color", show_props, "mat_hsv")
                if show_props.mat_hsv:
                    box = draw_inline_column(col.box(), "HSV:")
                    for socket in hsv_node.inputs[:-2]:
                        box.prop(socket, "default_value", text=socket.name)

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

        self.can_draw = drawn
        return
        # return drawn

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
