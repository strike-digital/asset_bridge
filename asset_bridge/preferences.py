import json
import os
from pathlib import Path

from .operators.op_check_for_new_assets import AB_OT_check_for_new_assets

from .helpers.library import ensure_bl_asset_library_exists, is_lib_path_invalid

from .operators.op_show_popup import show_popup
from .operators.op_open_folder import AB_OT_open_folder
from .operators.op_download_previews import AB_OT_download_previews
from .btypes import BMenu
from .api import get_asset_lists
from .settings import get_ab_settings
from .constants import ASSET_LIB_VERSION, DIRS, FILES, PREVIEW_DOWNLOAD_TASK_NAME, __IS_DEV__
from .helpers.ui import draw_download_previews, draw_downloads_path
from bpy.types import AddonPreferences, UILayout, Menu
from bpy.props import StringProperty


class ABAddonPreferences(AddonPreferences):
    bl_idname = __package__
    layout: UILayout

    def lib_path_set(self, new_path):
        """Update all references to library paths"""

        # Check that path is valid
        if is_lib_path_invalid(new_path):
            self["_lib_path"] = new_path
            return

        default_info_contents = {"version": ASSET_LIB_VERSION}

        # temporarily initialize a new files class at the new location to get the library info file
        temp_files = FILES.__class__()
        lib_info_file = temp_files.update(Path(new_path)).lib_info

        # Deal with potential future versions of the library
        if lib_info_file.exists():
            with open(lib_info_file, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    print(e)
                    data = default_info_contents
            version = data["version"]

            # Breaking update
            if version[0] > ASSET_LIB_VERSION[0]:
                message = """This folder has been created in a much newer version of the addon,
                and as such cannot be used by this version of the addon."""

                show_popup(message=message, title="Error", severity="WARNING")
                return

            # Major update
            elif version[1] > ASSET_LIB_VERSION[1] and not version[0] < ASSET_LIB_VERSION[0]:

                def confirm():
                    with open(lib_info_file, "w") as f:
                        json.dump(default_info_contents, f, indent=2)

                    self.lib_path = new_path

                message = """This folder has been used by a newer version of this addon,
                and as such it may not work with the current version.
                Are you sure you want to continue?"""
                show_popup(message=message, severity="WARNING", confirm=True, title="Warning!", confirm_func=confirm)
                return

        # Update referenecs
        self["_lib_path"] = str(new_path)
        DIRS.update()
        ensure_bl_asset_library_exists()

        # write to the config file
        with open(FILES.lib_info, "w") as f:
            json.dump(default_info_contents, f, indent=2)

    lib_path: StringProperty(
        name="External Downloads path",
        description=" ".join((
            "The path in which to save the downloaded assets.",
            "It's reccommended that you select a directory that won't be moved in the future",
        )),
        default="",
        subtype="DIR_PATH",
        get=lambda self: self.get("_lib_path", ""),
        set=lib_path_set,
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

        if draw_downloads_path(layout, context):
            # if the downloads path isn't valid
            return

        ab = get_ab_settings(context)
        lists_obj = get_asset_lists()

        # Draw the download previews button/progress bar
        new_assets_available = lists_obj.new_assets_available()
        # Check if there are new assets/whether they are already downloading
        if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys() or new_assets_available or not lists_obj.all_initialized:
            all_assets = lists_obj.all_assets
            preview_files = os.listdir(DIRS.previews)
            first_time = len(preview_files) == 0
            task = ab.tasks.get(PREVIEW_DOWNLOAD_TASK_NAME)
            task_steps = task.progress.max if task else 0

            # Draw info showing the number of previews to download, only if it is not the first time download
            if new_assets_available and task_steps != len(all_assets) and not first_time:
                needed_previews = set(a.idname for a in all_assets.values()) - {p.replace(".png", "") for p in preview_files}
                layout.label(text=self.format_download_label(needed_previews))

            # Draw the button/progress bar
            draw_download_previews(layout, reload=first_time)
            return

        row = layout.box().row(align=True)
        row.scale_y = 1.5

        op = row.operator_menu_hold(
            AB_OT_check_for_new_assets.bl_idname,
            icon="IMPORT",
            text="Check for new assets",
            menu=AB_MT_download_previews_menu.__name__,
        )
        op.bl_description = "Check for new assets, and if they exist, download their previews and update the library."

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
        op = layout.operator(AB_OT_download_previews.bl_idname, icon="FILE_REFRESH", text="Reload all assets")
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
