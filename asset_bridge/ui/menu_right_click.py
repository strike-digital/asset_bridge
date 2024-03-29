from ..helpers.btypes import ExecContext
import bpy
from bpy.types import UILayout
from ..settings import get_ab_settings
from ..operators.op_view_high_res_previews import AB_OT_view_high_res_previews
from .panel_asset_browser import AB_PT_asset_info


def draw_context_options(self, context):
    layout: UILayout = self.layout
    if not AB_PT_asset_info.poll(context):
        return

    layout.separator()
    urls = get_ab_settings(context).selected_asset.get_high_res_urls()
    row = layout.row(align=True)
    row.enabled = bool(urls)
    text = f"Show High Res Preview{'s' if len(urls) > 1 else ''}"
    AB_OT_view_high_res_previews.draw_button(row, text=text, exec_context=ExecContext.INVOKE)


def register():
    bpy.types.ASSETBROWSER_MT_context_menu.append(draw_context_options)


def unregister():
    bpy.types.ASSETBROWSER_MT_context_menu.remove(draw_context_options)
