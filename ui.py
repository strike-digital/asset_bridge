import bpy
from bpy.types import Panel, UILayout, Context
from .operators import AB_OT_import_asset, AB_OT_download_asset_previews
from .settings import AssetBridgeSettings
from .helpers import asset_preview_exists


def dpifac() -> float:
    """Taken from Node Wrangler. Not sure exacly why it works, but it is needed to get the visual position of nodes"""
    prefs = bpy.context.preferences.system
    return prefs.dpi * prefs.pixel_size / 72  # Why 72?


def draw_download_previews(layout: UILayout):
    layout = layout.box().column()
    layout.scale_y = 1.5
    ab = bpy.context.scene.asset_bridge
    if ab.download_status == "DOWNLOADING_PREVIEWS":
        layout.prop(ab, "preview_download_progress", text="Downloading")
    else:
        layout.operator(AB_OT_download_asset_previews.bl_idname, icon="IMPORT")
    return layout


class AB_PT_main_panel(Panel):
    """Creates a Panel"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Import"
    bl_category = "Asset Bridge"

    def draw(self, context: Context):
        layout: UILayout = self.layout
        ab: AssetBridgeSettings = context.scene.asset_bridge

        if ab.asset_name != "NONE":
            if not asset_preview_exists(ab.asset_name) or ab.download_status == "DOWNLOADING_PREVIEWS":
                draw_download_previews(layout)

        col = layout.column(align=False)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(ab, "filter_type", text="")
        row.prop(ab, "filter_categories", text="")
        col.separator(factor=.4)

        row = col.row(align=True)
        row.scale_y = 1.3
        width = context.region.width
        split = row.split(factor=(1 - (30 * dpifac()) / width), align=True)
        split.prop(ab, "filter_search", text="", icon="VIEWZOOM")
        asset_len = len(ab.get_assets())
        row = split.row(align=True)
        op = row.operator("asset_bridge.report_message", text=str(asset_len))
        op.message = f"There are {asset_len} assets that match your search"

        box = layout.box()
        box.template_icon_view(ab, "asset_name", scale=8, show_labels=True)
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.scale_y = .5
        label_text = "No assets found :(" if ab.asset_name == "NONE" else ab.asset_name.replace("_", " ").capitalize()
        row.label(text=label_text)
        box.prop(ab, "asset_quality", text="Quality")

        row = layout.row(align=True)
        row.scale_y = 1.5
        row.scale_x = 1.25

        if ab.download_status == "DOWNLOADING_ASSET":
            row.prop(ab, "ui_import_progress", text="Downloading:")
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
