from bpy.types import Menu

from ..api import get_asset_lists
from ..settings import get_asset_settings
from ..helpers.btypes import BMenu
from ..operators.op_swap_asset import AB_OT_swap_asset


@BMenu("Swap HDRI quality")
class AB_MT_swap_hdri_asset(Menu):

    def draw(self, context):
        world = context.scene.world
        layout = self.layout
        if not world:
            layout.label("No HDRI to swap")
            return

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Change quality level")

        layout.separator()

        settings = get_asset_settings(world)
        asset_name = settings.idname
        asset = get_asset_lists().all_assets[asset_name]
        for level_id, level_label, _ in asset.quality_levels:
            row = layout.row(align=True)
            if settings.quality_level == level_id:
                row.enabled = False
            icon = "CHECKMARK" if asset.is_downloaded(level_id) else "IMPORT"
            op: AB_OT_swap_asset = row.operator("asset_bridge.swap_asset", text=level_label, icon=icon)
            op.bl_description = f"Change this asset's quality level to {level_label}"
            op.to_quality = level_id
            op.asset_id = asset_name
