from . import wrap_text
from ..settings import get_ab_settings
from bpy_extras.asset_utils import AssetBrowserPanel
from ..constants import ASSET_LIB_NAME
from bpy.types import Panel
from ..btypes import BPanel


@BPanel(space_type="FILE_BROWSER", region_type="TOOLS", label="Asset Bridge")
class AB_PT_asset_browser(Panel, AssetBrowserPanel):

    @classmethod
    def poll(cls, context):
        if context.area.ui_type != "ASSETS":
            return False
        if not context.asset_file_handle:
            return False
        if ASSET_LIB_NAME != context.area.spaces.active.params.asset_library_ref:
            return False
        return cls.asset_browser_panel_poll(context)

    def draw(self, context):
        layout = self.layout
        ab = get_ab_settings(context)
        try:
            asset = ab.selected_asset
        except KeyError:
            wrap_text(context, "Asset not found", layout.box(), centered=True)
            return

        if not asset:
            return

        is_downloaded = asset.is_downloaded(ab.asset_quality)

        # Toprow
        col = layout.column(align=True)
        box = col.box()
        bigrow = box.row(align=True)
        row = bigrow.row(align=True)
        row.label(text="", icon="CHECKMARK" if is_downloaded else "IMPORT")
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
        # draw_asset_info(col, context, asset)
