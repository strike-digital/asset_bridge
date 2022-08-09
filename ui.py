from datetime import datetime
import bpy
from bpy.types import Panel, UILayout, Context
from .operators import AB_OT_import_asset, AB_OT_download_asset_previews
from .helpers import asset_preview_exists, Asset
from .settings import AssetBridgeSettings


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


def draw_info_row(layout: UILayout, label: str, value: str, prop: str = "") -> UILayout:
    row = layout.row(align=True)
    col1 = row.box().column(align=True)
    col1.scale_y = .75
    col1.label(text=label)
    if isinstance(value, str):
        value = [value]
    col = row.box().column(align=True)
    col.scale_y = col1.scale_y
    for val in value:
        if not prop:
            col.label(text="  " + val)
        if val != list(value)[0]:
            col1.label(text="")
    if prop:
        col.scale_y = col1.scale_y - .025
        col.prop(bpy.context.scene.asset_bridge, prop, expand=True, emboss=False)


class AB_PT_sort_panel(Panel):
    """Change the sorting options of the asset list"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_label = "Sort"

    def draw(self, context: Context):
        layout: UILayout = self.layout.column(align=True)
        ab: AssetBridgeSettings = context.scene.asset_bridge

        row = layout.row(align=True)
        split = row.split(align=True, factor=.3)
        split.label(text="Sort by:")
        col = split.column(align=True)
        col.prop(ab, "sort_options", expand=True)


class AB_PT_main_panel(Panel):
    """The main Asset Bridge panel"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Import"
    bl_category = "Asset Bridge"

    def draw(self, context: Context):
        layout: UILayout = self.layout
        ab: AssetBridgeSettings = context.scene.asset_bridge

        asset_found = ab.asset_name != "NONE"
        if asset_found:
            if not asset_preview_exists(ab.asset_name) or ab.download_status == "DOWNLOADING_PREVIEWS":
                draw_download_previews(layout)

        col = layout.column(align=False)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(ab, "filter_type", text="")
        row.prop(ab, "filter_categories", text="")
        col.separator(factor=.4)

        # Search bar
        row = col.row(align=True)
        row.scale_y = 1.3
        width = context.region.width
        button_size_px = 28
        split = row.split(factor=(button_size_px * dpifac()) / width, align=True)
        split.popover(AB_PT_sort_panel.__name__, text="", icon="SORTSIZE")

        button_size = (button_size_px * dpifac()) / (width - button_size_px - 3)
        split = split.split(factor=1 - button_size, align=True)
        split.prop(ab, "filter_search", text="", icon="VIEWZOOM")
        asset_len = len(ab.get_assets())
        row = split.row(align=True)
        op = row.operator("asset_bridge.report_message", text=str(asset_len))
        op.message = f"There are {asset_len} assets that match your search"

        # Asset picker
        box = layout.box()
        box.template_icon_view(ab, "asset_name", scale=8, show_labels=True)
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.scale_y = .5
        label_text = ab.asset_name.replace("_", " ").capitalize() if asset_found else "No assets found :("
        row.label(text=label_text)

        # Quality picker
        col = box.column(align=True)
        row = col.row(align=True)
        row.active = asset_found
        row.scale_y = 1.1
        row.scale_x = 1.05
        row.prop(ab, "show_asset_info", text="", icon="TRIA_DOWN" if ab.show_asset_info else "TRIA_RIGHT")
        row.prop(ab, "asset_quality", text="")

        # Asset info
        if ab.show_asset_info:
            asset: Asset = ab.selected_asset
            if asset:
                box = col.box().column(align=True)
                date_text = datetime.fromtimestamp(asset.date_published).strftime(format="%d/%m/%Y")
                suffix = "s" if len(asset.authors) > 1 else ""
                draw_info_row(box, f"Author{suffix}:", asset.authors.keys(), prop="info_authors")
                draw_info_row(box, "Downloads:", [f"{asset.download_count:,}"])
                if hasattr(asset, "dimensions"):
                    # Show dimensions in metric or imperial units depending on scene settings.
                    # This is my gift to the americans, burmese and the liberians of the world.
                    unit_system = context.scene.unit_settings.system
                    if unit_system == "METRIC" or unit_system == "NONE":
                        coefficient = 1
                        suffix = "m"
                    else:
                        coefficient = 3.2808399
                        suffix = "ft"
                    size_x = int((asset.dimensions.x // 1000) * coefficient)
                    size_y = int((asset.dimensions.y // 1000) * coefficient)
                    draw_info_row(box, "Dimensions:", f"{size_x}{suffix} x {size_y}{suffix}")

                if hasattr(asset, "evs"):
                    draw_info_row(box, "EVs:", str(asset.evs))
                if hasattr(asset, "whitebalance"):
                    draw_info_row(box, "Whitebalance:", str(asset.whitebalance) + "K")

                draw_info_row(box, "Date published:", date_text)
                if hasattr(asset, "date_taken"):
                    date_text = datetime.fromtimestamp(asset.date_taken).strftime(format="%d/%m/%Y")
                    draw_info_row(box, "Date taken:", date_text)

                suffix = "ies" if len(asset.categories) > 1 else "y"
                draw_info_row(box, f"Categor{suffix}:", asset.categories, prop="info_categories")

                suffix = "s" if len(asset.tags) > 1 else ""
                draw_info_row(box, f"Tag{suffix}:", asset.tags, prop="info_tags")
                # draw_info_row(box, f"Categor{suffix}:", asset.tags, prop="info_categories")

        row = layout.row(align=True)
        row.enabled = asset_found
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
