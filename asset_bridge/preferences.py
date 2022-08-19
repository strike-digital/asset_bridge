from bpy.types import AddonPreferences, UILayout
from .operators import AB_OT_clear_asset_folder, AB_OT_set_prop
from .ui import draw_download_previews
from .helpers import asset_preview_exists


class AddonPreferences(AddonPreferences):
    bl_idname = __package__
    layout: UILayout

    def draw(self, context):
        layout = self.layout
        ab = context.scene.asset_bridge
        if not asset_preview_exists(ab.asset_name) or ab.download_status == "DOWNLOADING_PREVIEWS":
            draw_download_previews(layout)
            return

        row = layout.row(align=True)
        row.scale_y = 1.5
        draw_download_previews(row, reload=True)
        row.operator(AB_OT_clear_asset_folder.bl_idname, icon="FILE_REFRESH")
        row.operator(
            "wm.url_open",
            icon="FUND",
            text="Support Polyhaven",
        ).url = "https://www.patreon.com/polyhaven/overview"
        if context.scene.asset_bridge.download_status != "NONE":
            op: AB_OT_set_prop = row.operator(AB_OT_set_prop.bl_idname, text="Reset download progress")
            op.data_path = "context.scene.asset_bridge"
            op.prop_name = "download_status"
            op.value = "NONE"
            op.eval_value = False
            op.bl_description = "Reset the download progress bar in case of an error causing it to get stuck"