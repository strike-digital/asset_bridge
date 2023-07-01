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
    layout.operator_context = "INVOKE_DEFAULT"
    urls = get_ab_settings(context).selected_asset.get_high_res_urls()
    row = layout.row(align=True)
    row.enabled = bool(urls)
    text = f"Show High Res Preview{'s' if len(urls) > 1 else ''}"
    row.operator(AB_OT_view_high_res_previews.bl_idname, text=text)


def register():
    bpy.types.ASSETBROWSER_MT_context_menu.append(draw_context_options)


def unregister():
    bpy.types.ASSETBROWSER_MT_context_menu.remove(draw_context_options)