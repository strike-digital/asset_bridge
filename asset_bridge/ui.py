from .constants import PREVIEW_DOWNLOAD_TASK_NAME
from bpy.types import UILayout
from .operators.op_download_previews import AB_OT_download_previews
import bpy


def draw_download_previews(layout: UILayout, reload: bool = False):
    if not reload:
        layout = layout.box().column()
        layout.scale_y = 1.5

    ab = bpy.context.window_manager.asset_bridge
    if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys():
        task = ab.tasks[PREVIEW_DOWNLOAD_TASK_NAME]
        layout.prop(
            task,
            "ui_progress_prop",
            text=task.progress.message
        )
    else:
        if reload:
            op = layout.operator(AB_OT_download_previews.bl_idname, icon="IMPORT", text="Check for new assets")
        else:
            op = layout.operator(AB_OT_download_previews.bl_idname, icon="IMPORT")
        op.bl_description = "Download the previews for all assets. This can take from 10s to a couple of minutes\
            depending on internet access."

    return layout