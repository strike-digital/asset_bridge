from pathlib import Path

from ..operators.op_initialize_asset_lists import AB_OT_initialize_asset_lists
from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..helpers.prefs import get_prefs
from ..helpers.library import is_lib_path_invalid
from ..operators.op_cancel_task import AB_OT_cancel_task
from ..operators.op_download_previews import AB_OT_download_previews
from ..constants import PREVIEW_DOWNLOAD_TASK_NAME
from bpy.types import Node, NodeSocket, UILayout, Context
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

    lists_obj = get_asset_lists()
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
        # If not all of the asset lists have been downloaded
        if not lists_obj.all_initialized:
            layout.operator(
                AB_OT_initialize_asset_lists.bl_idname,
                icon="IMPORT",
                text=text or "Download asset previews",
            )
        else:
            # Draw the download previews button
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


def draw_inline_column(layout: UILayout, label: str, factor: float = 0):
    """Create a split, draw a label on one side, and then return the other side"""
    split = layout.split(factor=factor or .3)
    row = split.row(align=True)
    if not label.endswith(":"):
        label += ":"
    row.label(text=label)
    col = split.column(align=True)
    return col


def draw_inline_prop(layout: UILayout, data, prop_name: str, col_label: str, prop_label: str, factor: float = 0):
    """Draw a property with the label on the left"""
    col = draw_inline_column(layout, col_label, factor)
    col.prop(data, prop_name, text=prop_label)
    return col


def draw_node_group_inputs(node: Node, layout: UILayout, context: Context, in_boxes: bool = False):
    """Draw the inputs of a node group, according to specific naming conventions"""
    col = layout.column(align=True)
    i = 0
    for socket in node.inputs:
        socket: NodeSocket
        if socket.links:
            continue
        if socket.name.startswith("-- ") and socket.name.endswith(" --"):
            new_group = socket.name[3:-3]
            if not new_group.endswith(":"):
                new_group = new_group + ":"
            box = col.box().column(align=True) if in_boxes else col.column(align=True)
            if i > 0:
                box.separator()
            split = box.split(factor=.3)
            row = split.row(align=True)
            row.label(text=new_group)
            box = split.column(align=True)
            continue

        socket.draw(context, box, socket.node, socket.name)
        i += 1
