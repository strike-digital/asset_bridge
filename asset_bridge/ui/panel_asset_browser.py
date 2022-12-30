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
        asset = ab.selected_asset
        if asset:
            layout.label(text=ab.selected_asset.label)
            layout.prop(ab, "asset_quality")
        