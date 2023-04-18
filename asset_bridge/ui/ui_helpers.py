from pathlib import Path

import blf
import bpy
from bpy.types import Node, Context, UILayout, NodeSocket

from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..constants import PREVIEW_DOWNLOAD_TASK_NAME
from ..helpers.prefs import get_prefs
from ..helpers.library import is_lib_path_invalid
from ..operators.op_cancel_task import AB_OT_cancel_task
from ..operators.op_download_previews import AB_OT_download_previews
from ..operators.op_initialize_asset_lists import AB_OT_initialize_asset_lists


class DummyLayout():
    """An immitator of the blender UILayout class, used so that the draw function can be run as a poll function"""

    def row(*args, **kwargs):
        return DummyLayout()

    def box(*args, **kwargs):
        return DummyLayout()

    def column(*args, **kwargs):
        return DummyLayout()

    def split(*args, **kwargs):
        return DummyLayout()

    def label(*args, **kwargs):
        return DummyLayout()

    def prop(*args, **kwargs):
        return DummyLayout()

    def menu(*args, **kwargs):
        return DummyLayout()

    def separator(*args, **kwargs):
        return DummyLayout()


def dpifac() -> float:
    """Taken from Node Wrangler"""
    prefs = bpy.context.preferences.system
    return prefs.dpi * prefs.pixel_size / 72  # Why 72?


def wrap_text(
    context: Context,
    text: str,
    layout: UILayout,
    centered: bool = False,
    width=0,
    splitter=None,
) -> list[str]:
    """Take a string and draw it over multiple lines so that it is never concatenated."""
    return_text = []
    row_text = ''

    width = width or context.region.width
    system = context.preferences.system
    ui_scale = system.ui_scale
    width = (4 / (5 * ui_scale)) * width

    dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11, dpi)

    for word in text.split(splitter):
        if word == "":
            return_text.append(row_text)
            row_text = ""
            continue
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


def draw_prefs_section(
    layout: UILayout,
    title: str,
    show_data=None,
    show_prop: str = "",
    index_prop: str = "",
) -> UILayout:
    """Draw a box with a title, and return it"""
    main_col = layout.column(align=True)

    box = main_col.box()
    col = box.column(align=True)
    col.scale_y = 0.85
    row = col.row(align=True)

    is_showing = True
    if show_data:
        if index_prop:
            index = getattr(show_data, index_prop)
            setattr(show_data, index_prop, index + 1)
            is_showing = getattr(show_data, show_prop)[index]
        else:
            index = -1
            is_showing = getattr(show_data, show_prop)
        sub = row.row(align=True)
        sub.prop(
            show_data,
            show_prop,
            index=index,
            text="",
            icon="TRIA_DOWN" if is_showing else "TRIA_RIGHT",
            emboss=False,
        )
        sub.scale_x = 1.2

    sub = row.row(align=True)
    sub.active = is_showing
    sub.label(text=title)
    sub.alignment = "CENTER"

    if show_data:
        # Use two separators to avoid making the box taller
        sub.separator(factor=3)
        sub.separator(factor=2)

    if not is_showing:
        return DummyLayout()

    box = main_col.box()
    col = box.column()
    return col


def draw_section_header(
    layout: UILayout,
    name: str,
    hide_prop_data=None,
    hide_prop_name=None,
    centered: bool = True,
    show_icon: bool = True,
    icon: str = "",
    right_padding: int = 6,
):
    """Draw a title in a box with a toggle"""
    box = layout.box()
    row = box.row(align=True)
    if hide_prop_data:
        if show_icon:
            arrow_icon = "TRIA_RIGHT" if not getattr(hide_prop_data, hide_prop_name) else "TRIA_DOWN"
            icon = icon or arrow_icon
            name += " " * right_padding
        else:
            icon = "NONE"
            row.active = not getattr(hide_prop_data, hide_prop_name)
        row.prop(hide_prop_data, hide_prop_name, text=name, emboss=False, icon=icon)
    else:
        if centered:
            row.alignment = "CENTER"
        icon = icon or "NONE"
        row.label(text=name, icon=icon)
    return row


def draw_task_progress(layout: UILayout, context: Context, task_name: str, text="", draw_cancel=True):
    """Draw a progress bar for a task that draws either the progress message or the given text,
    and a cancel button, if that is enabled"""

    ab = get_ab_settings(context)
    row = layout.row(align=True)
    task = ab.tasks[task_name]
    row.prop(task, "ui_progress_prop", text=text or task.progress.message)
    if draw_cancel:
        row.scale_x = 1.25
        op = row.operator(AB_OT_cancel_task.bl_idname, text="", icon="X")
        op.name = task_name
        op.bl_description = "Cancel task"


def draw_download_previews(layout: UILayout, text="", reload=False, in_box: bool = True):
    """Draw the button and interface for downloading the asset previews"""
    if in_box:
        layout = layout.box().column()
        layout.scale_y = 1.5

    lists_obj = get_asset_lists()
    ab = get_ab_settings(bpy.context)

    if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys():
        task = ab.tasks[PREVIEW_DOWNLOAD_TASK_NAME]
        task.draw_progress(layout)
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


def draw_node_group_inputs(
    node: Node,
    layout: UILayout,
    context: Context,
    in_boxes: bool = False,
    spacing: float = 1.,
    factor: float = .3,
):
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
                box.separator(factor=spacing)
            split = box.split(factor=factor)
            row = split.row(align=True)
            row.label(text=new_group)
            box = split.column(align=True)
            continue

        socket.draw(context, box, socket.node, socket.name)
        i += 1
        i += 1