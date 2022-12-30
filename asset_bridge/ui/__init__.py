from pathlib import Path

from ..settings import get_ab_settings
from ..helpers.prefs import get_prefs
from ..helpers.library import is_lib_path_invalid
from ..operators.op_cancel_task import AB_OT_cancel_task
from ..operators.op_download_previews import AB_OT_download_previews
from ..constants import PREVIEW_DOWNLOAD_TASK_NAME
from bpy.types import UILayout, Context
import bpy
import blf


def dpifac() -> float:
    """Taken from Node Wrangler"""
    prefs = bpy.context.preferences.system
    return prefs.dpi * prefs.pixel_size / 72  # Why 72?


def wrap_text(context: Context, text: str, layout: UILayout, centered: bool = False, width=0) -> list[str]:
    """Take a string and draw it over multiple lines so that it is never concatenated."""
    return_text = []
    row_text = ''

    width = width or context.region.width
    system = context.preferences.system
    ui_scale = system.ui_scale
    width = (4 / (5 * ui_scale)) * width

    dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11, dpi)

    for word in text.split():
        word = f' {word}'
        line_len, _ = blf.dimensions(0, row_text + word)

        if line_len <= (width - 16):
            row_text += word
        else:
            return_text.append(row_text)
            row_text = word

    if row_text:
        return_text.append(row_text)

    for text in return_text:
        row = layout.row()
        if centered:
            row.alignment = "CENTER"
        row.label(text=text)

    return return_text


def draw_download_previews(layout: UILayout, text="", reload=False, in_box: bool = True):
    """Draw the button and interface for downloading the asset previews"""
    if in_box:
        layout = layout.box().column()
        layout.scale_y = 1.5

    ab = get_ab_settings(bpy.context)
    if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys():
        row = layout.row(align=True)
        task = ab.tasks[PREVIEW_DOWNLOAD_TASK_NAME]
        row.prop(task, "ui_progress_prop", text=task.progress.message)
        row.scale_x = 1.25
        op = row.operator(AB_OT_cancel_task.bl_idname, text="", icon="X")
        op.name = PREVIEW_DOWNLOAD_TASK_NAME
        op.bl_description = "Cancel downloading previews"
    else:
        op = layout.operator(AB_OT_download_previews.bl_idname, icon="IMPORT", text=text or "Download previews")
        op.bl_description = "Download the previews for all assets. This can take from 10s to a couple of minutes\
            depending on internet access."

        op.reload = reload

    return layout


def draw_downloads_path(layout: UILayout, context: Context):
    col = layout.box().column(align=True)
    col.label(text="External Downloads Path:")
    prefs = get_prefs(context)
    row = col.row(align=True)
    row.scale_y = row.scale_x = 1.5
    if message := is_lib_path_invalid(Path(prefs.lib_path)):
        row.alert = True
        row2 = col.row(align=True)
        row2.alert = True
        row2.label(text=message)
    row.prop(prefs, "lib_path", text="")
    return message