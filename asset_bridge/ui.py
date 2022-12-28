from pathlib import Path
from .helpers.library import is_lib_path_valid
from .helpers.prefs import get_prefs
from .operators.op_cancel_task import AB_OT_cancel_task
from .operators.op_download_previews import AB_OT_download_previews
from .constants import PREVIEW_DOWNLOAD_TASK_NAME
from bpy.types import UILayout, Context
import bpy


def draw_download_previews(layout: UILayout, text="", in_box: bool = True):
    """Draw the button and interface for downloading the asset previews"""
    if in_box:
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
        op = layout.operator(AB_OT_download_previews.bl_idname, icon="IMPORT", text=text or"Download previews")
        op.bl_description = "Download the previews for all assets. This can take from 10s to a couple of minutes\
            depending on internet access."

    return layout


def draw_downloads_path(layout: UILayout, context: Context):
    col = layout.box().column(align=True)
    col.label(text="External Downloads Path:")
    prefs = get_prefs(context)
    row = col.row(align=True)
    row.scale_y = row.scale_x = 1.5
    if message := is_lib_path_valid(Path(prefs.lib_path)):
        row.alert = True
        row2 = col.row(align=True)
        row2.alert = True
        row2.label(text=message)
    row.prop(prefs, "lib_path", text="")
    return message