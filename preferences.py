from bpy.types import AddonPreferences, UILayout
from .operators import AB_OT_clear_asset_folder
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
        
        layout.operator(AB_OT_clear_asset_folder.bl_idname)