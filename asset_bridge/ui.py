from datetime import datetime
from .constants import BL_ASSET_LIB_NAME, DIRS
import bpy
from bpy.types import Panel, UILayout, Context
from bpy_extras.asset_utils import AssetBrowserPanel
from .operators import AB_OT_import_asset, AB_OT_download_asset_previews, AB_OT_open_author_website
from .helpers import asset_preview_exists, get_prefs
from .assets import Asset, asset_list
from .settings import AssetBridgeSettings, BrowserSettings


def dpifac() -> float:
    """Taken from Node Wrangler. Not sure exacly why it works, but it is needed to get the visual position of nodes"""
    prefs = bpy.context.preferences.system
    return prefs.dpi * prefs.pixel_size / 72  # Why 72?


def draw_downloads_path(layout: UILayout, context: Context):
    col = layout.box().column(align=True)
    col.label(text="External Downloads Path:")
    prefs = get_prefs(context)
    row = col.row(align=True)
    row.scale_y = row.scale_x = 1.5
    if not DIRS.is_valid:
        row.alert = True
        row2 = col.row(align=True)
        row2.alert = True
        row2.label(text=DIRS.invalid_message)
    row.prop(prefs, "lib_path", text="")
    return DIRS.is_valid


def draw_download_previews(layout: UILayout, reload: bool = False):
    if not reload:
        layout = layout.box().column()
        layout.scale_y = 1.5

    ab = bpy.context.scene.asset_bridge.panel
    if ab.preview_download_progress_active:
        layout.prop(ab, "ui_preview_download_progress", text=asset_list.progress.message)
    else:
        if reload:
            op = layout.operator(AB_OT_download_asset_previews.bl_idname, icon="IMPORT", text="Check for new assets")
        else:
            op = layout.operator(AB_OT_download_asset_previews.bl_idname, icon="IMPORT")
        op.bl_description = "Download the previews for all assets. This can take from 10s to a couple of minutes\
            depending on internet access."

    return layout


def draw_info_row(layout: UILayout, label: str, values: str, operator: str = "", icon="NONE") -> UILayout:
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
        right.label(text=f" {val}", icon=icon)
     
        """This is some magic that places the operator button on top of the label,
        which allows the text to be left aligned rather than in the center.
        It works by creating a dummy row above the operator, and then giving it a negative scale,
        which pushes the operator up to be directly over the text.
        If you want to see what it's doing, set emboss to True and change the sub.scale_y parameter.
        It is also entirely overkill"""
        if operator:
            subcol = right.column(align=True)
            sub = subcol.column(align=True)
            sub.scale_y = -1
            sub.prop(bpy.context.scene.asset_bridge.panel, "sort_ascending")
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


def draw_asset_info(layout: UILayout, context: Context, asset: Asset):
    col = layout.column(align=True)
    op = draw_info_row(col, "Link:", ["Polyhaven.com"], operator="wm.url_open")[0]
    op.url = asset.asset_webpage_url
    # Authors
    suffix = "s" if len(asset.authors) > 1 else ""
    ops = draw_info_row(
        col,
        f"Author{suffix}:",
        asset.authors.keys(),
        operator=AB_OT_open_author_website.bl_idname,
    )
    for author, op in zip(asset.authors, ops):
        op.author_name = author
        op.bl_description = f"Open {author}'s website"

    op = draw_info_row(
        col,
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
        draw_info_row(col, "Dimensions:", f"{size_x}{suffix} x {size_y}{suffix}")

    if hasattr(asset, "evs"):
        draw_info_row(col, "EVs:", str(asset.evs))
    if hasattr(asset, "whitebalance"):
        draw_info_row(col, "Whitebalance:", f"{str(asset.whitebalance)}K")

    date_text = datetime.fromtimestamp(asset.date_published).strftime(format="%d/%m/%Y")
    draw_info_row(col, "Date published:", date_text)
    if hasattr(asset, "date_taken"):
        date_text = datetime.fromtimestamp(asset.date_taken).strftime(format="%d/%m/%Y")
        draw_info_row(col, "Date taken:", date_text)

    suffix = "ies" if len(asset.categories) > 1 else "y"
    draw_info_row(col, f"Categor{suffix}:", asset.categories)

    suffix = "s" if len(asset.tags) > 1 else ""
    draw_info_row(col, f"Tag{suffix}:", asset.tags)


class AB_PT_main_panel(Panel):
    """The main Asset Bridge panel"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Import"
    bl_category = "Asset Bridge"

    def draw(self, context: Context):
        layout: UILayout = self.layout
        ab: AssetBridgeSettings = context.scene.asset_bridge.panel

        if not DIRS.is_valid:
            draw_downloads_path(layout, context)
            return

        asset_found = ab.asset_name != "NONE"
        # if asset_found and (not asset_preview_exists(ab.asset_name) or ab.download_status == "DOWNLOADING_PREVIEWS"):
        if asset_found and (not asset_preview_exists(ab.asset_name) or ab.preview_download_progress_active):
            draw_download_previews(layout)
            return

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
        asset: Asset = ab.selected_asset
        if ab.show_asset_info and asset:
            box = col.box()
            draw_asset_info(box, context, asset)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.enabled = asset_found
        row.scale_y = 1.5
        row.scale_x = 1.25

        downloaded = asset.get_file_path(ab.asset_quality).exists() if asset else False
        if ab.import_progress_active:
            row.prop(ab, "ui_import_progress", text="Downloading:")
        else:
            if downloaded:
                op = row.operator_menu_hold(
                    AB_OT_import_asset.bl_idname,
                    menu=AB_MT_import_menu.bl_idname,
                    text="Import Asset",
                    icon="CHECKMARK",
                )
                op.reload = False
            else:
                op = row.operator(
                    AB_OT_import_asset.bl_idname,
                    icon="IMPORT",
                    text="Download Asset",
                )
                op.reload = False
            # op.link = True
            op.from_asset_browser = False
            op.link = ab.import_method == "LINK"

        row.prop(ab, "show_import_settings", text="", icon="PREFERENCES")
        if ab.show_import_settings:
            box = col.box().box().column()
            box.prop(ab, "import_method", text="")
            # box.label(text="hoho")
        # row.prop(ab, "show_import_settings", text="", icon="TRIA_DOWN" if ab.show_import_settings else "TRIA_")
        # row.prop(ab, "asset_quality", text="", icon="PREFERENCES", icon_only=True)
        # row.scale_x = .7
        # row.popover(AB_PT_sort_panel.__name__, text="", icon="PREFERENCES")
        # row.popover_group("VIEW_3D", "UI", "", "Alpha Trees")
        # op = row.operator("wm.url_open", text="", icon="URL")
        # op.url = asset.asset_webpage_url if asset else "https://polyhaven.com/"

        if context.object and (mat := context.object.active_material):
            nodes = mat.node_tree.nodes
            if mapping_node := nodes.get("Mapping"):
                layout = layout.box()
                col = layout.column()
                col.prop(mapping_node.inputs[3], "default_value", text="Texture scale")
            if displace_node := nodes.get("Displacement"):
                layout = layout.box()
                layout.prop(displace_node, "mute", text="Use displacement", invert_checkbox=True)


class AB_PT_sort_panel(Panel):
    """Change the sorting options of the asset list"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_label = "Sort"

    def draw(self, context: Context):
        layout: UILayout = self.layout
        ab: AssetBridgeSettings = context.scene.asset_bridge.panel

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


class AB_MT_import_menu(bpy.types.Menu):
    bl_label = "Import options"
    bl_idname = "AB_MT_import_menu"

    def draw(self, context):
        layout: UILayout = self.layout
        layout.scale_y = 1.2
        op = layout.operator(AB_OT_import_asset.bl_idname, text="Redownload asset", icon="FILE_REFRESH")
        op.from_asset_browser = False
        op.reload = True


class AB_PT_browser_settings_panel(Panel, AssetBrowserPanel):
    bl_region_type = "TOOLS"
    bl_label = "Asset Bridge"
    # bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return all((
            context.asset_file_handle,
            BL_ASSET_LIB_NAME in context.area.spaces.active.params.asset_library_ref,
            cls.asset_browser_panel_poll(context),
        ))

    def draw(self, context):
        layout: UILayout = self.layout
        ab: BrowserSettings = context.scene.asset_bridge.browser
        if (asset := ab.selected_asset) or (asset := ab.previous_asset):
            downloaded = asset.get_file_path(ab.asset_quality).exists() and not ab.import_progress_active
            col = layout.column(align=True)
            box = col.box()
            bigrow = box.row(align=True)
            row = bigrow.row(align=True)
            row.label(text="", icon="CHECKMARK" if downloaded else "IMPORT")
            row = bigrow.row(align=True)
            row.alignment = "CENTER"
            # row.template_icon()
            text = "   " + asset.label if downloaded else asset.label + "    "
            row.label(text=text)
            if downloaded:
                row = bigrow.row(align=True)
                row.alignment = "RIGHT"
                row.prop(ab, "reload_asset", text="", icon="FILE_REFRESH", emboss=ab.reload_asset)
            box = col.box()
            box.prop(ab, "asset_quality", text="Quality")
            draw_asset_info(col, context, asset)


def status_bar_draw(self, context):
    layout: UILayout = self.layout
    ab: BrowserSettings = context.scene.asset_bridge.browser
    if ab.import_progress_active:
        layout.prop(ab, "ui_import_progress", text="Downloading asset:")


def register():
    bpy.types.STATUSBAR_HT_header.prepend(status_bar_draw)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(status_bar_draw)