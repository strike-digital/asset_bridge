from bpy.types import UILayout
import bpy


def draw_download_previews(layout: UILayout, reload: bool = False):
    if not reload:
        layout = layout.box().column()
        layout.scale_y = 1.5

    ab = bpy.context.window_manager.asset_bridge
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