import os

from .operators.op_open_folder import AB_OT_open_folder

from .operators.op_download_previews import AB_OT_download_previews

from .btypes import BMenu

from .api import get_asset_lists
from .settings import get_ab_settings
from .constants import DIRS, PREVIEW_DOWNLOAD_TASK_NAME, __IS_DEV__
from .ui import draw_download_previews, draw_downloads_path
from bpy.types import AddonPreferences, UILayout, Menu
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

    def format_download_label(self, needed_previews):
        needed_previews = list(needed_previews)
        assets_str = str(needed_previews[:3])[1:-1].replace("'", "").replace("_", " ")
        assets_str = assets_str + ("..." if len(needed_previews) > 3 else "")

        number_needed = len(needed_previews)
        are = "are" if number_needed > 1 else "is"
        s = "s" if number_needed > 1 else ""
        return f"There {are} {number_needed} new preview{s} to download ({assets_str})"

    def draw(self, context):
        layout = self.layout
        ab = get_ab_settings(context)
        all_assets = get_asset_lists().all_assets

        # Draw the download previews button/progress bar
        preview_files = os.listdir(DIRS.previews)
        new_assets_available = len(all_assets) > len(preview_files)
        # Check if there are new assets/whether they are already downloading
        if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys() or new_assets_available:
            first_time = len(preview_files) == 0
            task = ab.tasks.get(PREVIEW_DOWNLOAD_TASK_NAME)
            task_steps = task.progress.max if task else 0

            # Draw info showing the number of previews to download, only if it is not the first time download
            if new_assets_available and task_steps != len(all_assets) and not first_time:
                needed_previews = set(all_assets) - {p.replace(".png", "") for p in preview_files}
                layout.label(text=self.format_download_label(needed_previews))

            # Draw the button/progress bar
            draw_download_previews(layout, reload=first_time)
            return

        draw_downloads_path(layout, context)

        row = layout.box().row(align=True)
        row.scale_y = 1.5

        op = row.operator_menu_hold(
            AB_OT_download_previews.bl_idname,
            icon="IMPORT",
            text="Check for new assets",
            menu=AB_MT_download_previews_menu.__name__,
        )
        op.bl_description = "Check for new assets, and if they exist, download their previews and update the library."
        op.reload = False

        # draw_download_previews(row, in_box=False, text="Check for new assets", reload=False)
        row.operator(
            "wm.url_open",
            icon="FUND",
            text="Support Polyhaven",
        ).url = "https://www.patreon.com/polyhaven/overview"


@BMenu()
class AB_MT_download_previews_menu(Menu):

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.5
        op = layout.operator(AB_OT_download_previews.bl_idname, icon="IMPORT", text="Reload all assets")
        op.bl_description = "Redownload all previews and re setup the asset catalog again (good for debugging)"
        op.reload = True

        if __IS_DEV__:
            op = layout.operator(AB_OT_download_previews.bl_idname, icon="FILE_SCRIPT", text="Debug test")
            op.bl_description = "download a small subset of the assets, for speed"
            op.reload = True
            op.test_number = 100

        op = layout.operator(AB_OT_open_folder.bl_idname, text="Open previews folder", icon="FILE_FOLDER")
        op.bl_description = "Open the folder containing the preview files"
        op.file_path = str(DIRS.previews)
