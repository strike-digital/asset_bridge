from bpy.types import Panel
from bpy_extras.asset_utils import AssetBrowserPanel

from ..settings import get_ab_settings
from ..constants import DIRS, ASSET_LIB_NAME
from .ui_helpers import wrap_text
from ..helpers.btypes import BPanel


@BPanel(space_type="FILE_BROWSER", region_type="TOOLS", label="Asset Bridge")
class AB_PT_asset_browser(Panel, AssetBrowserPanel):

    @classmethod
    def poll(cls, context):
        if context.area.ui_type != "ASSETS":
            return False
        if not context.asset_file_handle:
            return False
        # In 3.5 the assets can also be viewed in th "All" asset library
        if ASSET_LIB_NAME != context.area.spaces.active.params.asset_library_ref:
            ab = get_ab_settings(context)
            try:
                asset = ab.selected_asset
            except KeyError:
                asset = None

            if not asset:
                return False
        return cls.asset_browser_panel_poll(context)

    def draw(self, context):
        layout = self.layout
        ab = get_ab_settings(context)
        try:
            asset = ab.selected_asset
        except KeyError:
            asset = None

        if not asset:
            if context.area.spaces.active.params.asset_library_ref != ASSET_LIB_NAME:
                return
            box = layout.box()
            box.alert = True
            wrap_text(context, "Asset not found", box, centered=True)
            return

        if message := asset.poll():
            box = layout.box()
            box.separator()
            box.alert = True
            box.scale_y = .45
            wrap_text(context, message, box, centered=True)
            box.separator()
            return

        is_downloaded = asset.is_downloaded(ab.asset_quality)

        # Toprow
        col = layout.column(align=True)
        box = col.box()
        bigrow = box.row(align=True)
        row = bigrow.row(align=True)
        if is_downloaded:
            op = row.operator("asset_bridge.open_folder", text="", icon="FILE_FOLDER", emboss=False)
            op.file_path = str(asset.downloads_dir)
        else:
            op = row.operator("asset_bridge.open_folder", text="", icon="IMPORT", emboss=False)
            op.file_path = str(DIRS.assets)

        row = bigrow.row(align=True)
        row.alignment = "CENTER"
        text = "   " + asset.label if is_downloaded else asset.label + "    "
        row.label(text=text)

        if is_downloaded:
            row = bigrow.row(align=True)
            row.alignment = "RIGHT"
            row.prop(ab, "reload_asset", text="", icon="FILE_REFRESH", emboss=ab.reload_asset)

        box = col.box()
        box.prop(ab, "asset_quality", text="Quality")

        col = box.column(align=True)
        metadata = asset.metadata
        for item in metadata:
            item.draw(col, context)
