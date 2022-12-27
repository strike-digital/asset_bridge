from .operators.op_cancel_task import AB_OT_cancel_task
from .constants import PREVIEW_DOWNLOAD_TASK_NAME
from bpy.types import UILayout
from .operators.op_download_previews import AB_OT_download_previews
import bpy


def draw_download_previews(layout: UILayout):
    layout = layout.box().column()
    layout.scale_y = 1.5

    ab = bpy.context.window_manager.asset_bridge
    if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys():
        row = layout.row(align=True)
        task = ab.tasks[PREVIEW_DOWNLOAD_TASK_NAME]
        row.prop(task, "ui_progress_prop", text=task.progress.message)
        row.scale_x = 1.25
        op = row.operator(AB_OT_cancel_task.bl_idname, text="", icon="X")
        op.name = PREVIEW_DOWNLOAD_TASK_NAME
        op.bl_description = "Cancel downloading previews"
    else:
        op = layout.operator(AB_OT_download_previews.bl_idname, icon="IMPORT", text="Download previews")
        op.bl_description = "Download the previews for all assets. This can take from 10s to a couple of minutes\
            depending on internet access."

    return layout