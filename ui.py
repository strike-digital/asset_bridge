from datetime import datetime
import bpy
from bpy.types import Panel, UILayout, Context
from .operators import AB_OT_import_asset, AB_OT_download_asset_previews, AB_OT_open_author_website, AB_OT_set_ab_prop
from .helpers import asset_preview_exists, Asset, asset_list
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


def draw_info_row(layout: UILayout, label: str, values: str, operator: str = "") -> UILayout:
    row = layout.row(align=True)
    split = row.split(align=True)
    left = split.box().column(align=True)
    left.label(text=label)
    left.scale_y = .75
    if isinstance(values, str):
        values = [values]
    right_row = split.box().row(align=True)
    right = right_row.column(align=True)
    right.scale_y = left.scale_y
    ops = []
    for val in values:
        right.alignment = "LEFT"
        right.label(text=f" {val}")
        # if operator:
        #     subrow = row.row(align=True)
        #     subrow.alignment = "RIGHT"
        #     subrow.active = False
        #     op = subrow.operator(operator, text="", emboss=False, icon=icon)
        """This is some magic that places the operator button on top of the label,
        which allows the text to be left aligned rather than in the center.
        It works by creating a dummy row above the operator, and then giving it a negative scale,
        which pushes the operator up to be directly over the text.
        If you want to see what it's doing, set emboss to True and change the sub.scale_y parameter."""
        if operator:
            subcol = right.column(align=True)
            sub = subcol.column(align=True)
            sub.scale_y = -1
            sub.prop(bpy.context.scene.asset_bridge, "sort_ascending")
            subrow = subcol.row(align=True)
            op = subrow.operator(operator, text="", emboss=True)
            ops.append(op)
        if val != list(values)[0]:
            left.label(text="")
    # col = right_row.column(align=True)
    # col.alignment = "RIGHT"
    # col.scale_y = left.scale_y
    # col.active = False
    return ops


class AB_PT_sort_panel(Panel):
    """Change the sorting options of the asset list"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_label = "Sort"

    def draw(self, context: Context):
        layout: UILayout = self.layout
        ab: AssetBridgeSettings = context.scene.asset_bridge

        row = layout.row(align=True)
        split = row.split(align=True, factor=.3)
        split.label(text="Sort by:")
        col = split.column(align=True)
        col.prop(ab, "sort_method", expand=True)

        row = layout.row(align=True)
        split = row.split(align=True, factor=.3)
        split.label(text="Sort order:")
        col = split.column(align=True)
        col.prop(ab, "sort_order", expand=True)


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
        if asset_found and (not asset_preview_exists(ab.asset_name) or ab.download_status == "DOWNLOADING_PREVIEWS"):
            draw_download_previews(layout)

        # The asset list can't be sorted at register because scene properties can't be accessed,
        # So sort it here
        if not asset_list.sorted:
            asset_list.sort(ab.sort_method, ab.sort_ascending)

        col = layout.column(align=False)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(ab, "filter_type", text="")
        row.prop(ab, "filter_category", text="")
        col.separator(factor=.4)

        # Search bar
        row = col.row(align=True)
        row.scale_y = 1.3
        width = context.region.width
        button_size_px = 28
        split = row.split(factor=(button_size_px * dpifac()) / width, align=True)
        # if ab.sort_method:
        icon = {i[0]: i[3] for i in ab.sort_method_items(context)}[ab.sort_method]
        split.popover(AB_PT_sort_panel.__name__, text="", icon=icon)

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
                emboss = False
                box = col.box().column(align=True)

                # Authors
                suffix = "s" if len(asset.authors) > 1 else ""
                ops = draw_info_row(
                    box,
                    f"Author{suffix}:",
                    asset.authors.keys(),
                    operator=AB_OT_open_author_website.bl_idname,
                )
                for author, op in zip(asset.authors, ops):
                    op.author_name = author
                    op.bl_description = f"Open {author}'s website"

                op = draw_info_row(
                    box,
                    "Downloads:",
                    [f"{asset.download_count:,}"],
                    # operator=AB_OT_set_ab_prop.bl_idname,
                )
                # op.prop_name = "sort_method"
                # op.value = "DOWNLOADS"
                # op.bl_description = "Sort assets by number of downloads"
                # op.message = "Sorting assets by number of downloads"
                # row = col.row(align=True)
                # row.alignment = "RIGHT"
                # op: AB_OT_set_ab_prop = row.operator(
                #     AB_OT_set_ab_prop.bl_idname,
                #     text="",
                #     icon="SORTSIZE",
                #     emboss=emboss,
                # )
                # op.prop_name = "sort_method"
                # op.value = "DOWNLOADS"
                # op.bl_description = "Sort assets by downloads"

                if hasattr(asset, "dimensions"):
                    # Show dimensions in metric or imperial units depending on scene settings.
                    # This is my gift to the americans, burmese and the liberians of the world.
                    unit_system = context.scene.unit_settings.system
                    if unit_system in ["METRIC", "NONE"]:
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
                    draw_info_row(box, "Whitebalance:", f"{str(asset.whitebalance)}K")

                date_text = datetime.fromtimestamp(asset.date_published).strftime(format="%d/%m/%Y")
                draw_info_row(box, "Date published:", date_text)
                if hasattr(asset, "date_taken"):
                    date_text = datetime.fromtimestamp(asset.date_taken).strftime(format="%d/%m/%Y")
                    draw_info_row(box, "Date taken:", date_text)

                suffix = "ies" if len(asset.categories) > 1 else "y"
                draw_info_row(box, f"Categor{suffix}:", asset.categories)

                suffix = "s" if len(asset.tags) > 1 else ""
                draw_info_row(box, f"Tag{suffix}:", asset.tags)

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
