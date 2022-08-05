from bpy.types import Panel, UILayout, Context
from .operators import AB_OT_import_asset, AB_OT_check_for_new_assets, AB_OT_clear_asset_folder
from .settings import AssetBridgeSettings


class AB_PT_main_panel(Panel):
    """Creates a Panel"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Import"
    bl_category = "Asset Bridge"

    def draw(self, context: Context):
        layout: UILayout = self.layout
        ab: AssetBridgeSettings = context.scene.asset_bridge
        op = layout.operator(AB_OT_check_for_new_assets.bl_idname)
        op = layout.operator(AB_OT_clear_asset_folder.bl_idname)

        layout.prop(ab, "filter_type", text="Type")
        # layout.prop(ab, "asset_name", text="Asset")

        if not ab.asset_name:
            return

        box = layout.box()
        box.template_icon_view(
            ab,
            "asset_name",
            scale=8,
        )
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.scale_y = .5
        row.label(text=ab.asset_name.replace("_", " ").capitalize())
        box.prop(ab, "asset_quality", text="Quality")

        # print(AB_OT_import_asset.asset)
        # if asset := AB_OT_import_asset.asset:

        row = layout.row(align=True)
        row.scale_y = 1.5
        row.scale_x = 1.25

        if ab.import_stage != "NONE":
            row.prop(ab, "ui_import_progress", text=ab.import_stage.title() + ":")
        else:
            op = row.operator(AB_OT_import_asset.bl_idname)
            op.reload = ab.reload_asset
        row.prop(ab, "reload_asset", text="", icon="FILE_REFRESH")

        if context.object and (mat := context.object.active_material):
            nodes = mat.node_tree.nodes
            if mapping_node := nodes.get("Mapping"):
                layout = layout.box()
                col = layout.column()
                col.prop(mapping_node.inputs[3], "default_value", text="Texture scale")
            if displace_node := nodes.get("Displacement"):
                layout = layout.box()
                layout.prop(displace_node, "mute", text="Use displacement", invert_checkbox=True)
