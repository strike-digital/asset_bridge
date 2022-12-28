import os

from .api import get_apis
from .settings import AssetBridgeSettings
from .constants import DIRS, PREVIEW_DOWNLOAD_TASK_NAME
from .ui import draw_download_previews, draw_downloads_path
from bpy.types import AddonPreferences, UILayout
from bpy.props import StringProperty


class ABAddonPreferences(AddonPreferences):
    bl_idname = __package__
    layout: UILayout

    def lib_path_update(self, context):
        """Update all references to library paths"""
        print("lib_path_update")

    lib_path: StringProperty(
        name="External Downloads path",
        description=" ".join((
            "The path in which to save the downloaded assets.",
            "It's reccommended that you select a directory that won't be moved in the future",
        )),
        default="",
        subtype="DIR_PATH",
        update=lib_path_update,
    )

    def draw(self, context):
        layout = self.layout
        ab: AssetBridgeSettings = context.window_manager.asset_bridge
        assets = get_apis().all_assets

        preview_files = os.listdir(DIRS.previews)
        if len(preview_files) != len(assets) or PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys():
            draw_download_previews(layout)
            return

        draw_downloads_path(layout, context)

        row = layout.box().row(align=True)
        row.scale_y = 1.5
        draw_download_previews(row, in_box=False, text="Redownload previews")
        row.operator(
            "wm.url_open",
            icon="FUND",
            text="Support Polyhaven",
        ).url = "https://www.patreon.com/polyhaven/overview"
