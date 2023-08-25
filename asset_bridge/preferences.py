import os
import json
from pathlib import Path
from .operators.op_open_log_file import AB_OT_open_log_file

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import Menu, UILayout, AddonPreferences

from .api import get_asset_lists
from .previews import ICONS
from .settings import new_show_prop, get_ab_settings
from .constants import (
    DIRS,
    FILES,
    __IS_DEV__,
    ASSET_LIB_VERSION,
    CHECK_NEW_ASSETS_TASK_NAME,
    PREVIEW_DOWNLOAD_TASK_NAME,
)
from .helpers.prefs import get_prefs
from .ui.ui_helpers import wrap_text, draw_inline_prop, draw_inline_column, draw_prefs_section, draw_download_previews
from .helpers.btypes import BMenu
from .helpers.library import is_lib_path_invalid, ensure_bl_asset_library_exists
from .addon_updater_ops import UpdaterPreferences, draw_update_settings_ui
from .ui.panel_3d_viewport import AB_PT_asset_props_viewport
from .operators.op_show_info import InfoSnippets
from .ui.panel_asset_browser import AB_PT_asset_info
from .operators.op_show_popup import show_popup
from .operators.op_open_folder import AB_OT_open_folder
from .operators.op_remove_task import AB_OT_remove_task
from .operators.op_report_message import report_message
from .operators.op_download_previews import AB_OT_download_previews
from .operators.op_check_for_new_assets import AB_OT_check_for_new_assets
from .operators.op_create_dummy_assets import AB_OT_create_dummy_assets


class ABAddonPreferences(UpdaterPreferences, AddonPreferences):
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
        DIRS.update(new_path)
        # print(DIRS.)
        ensure_bl_asset_library_exists()

        # write to the config file
        with open(FILES.lib_info, "w") as f:
            json.dump(default_info_contents, f, indent=2)

    lib_path: StringProperty(
        name="External Downloads path",
        description=" ".join(
            (
                "The path in which to save the downloaded assets.",
                "It's reccommended that you select a directory that won't be moved in the future",
            )
        ),
        default="",
        subtype="DIR_PATH",
        get=lambda self: self.get("_lib_path", ""),
        set=lib_path_set,
    )

    def viewport_panel_category_update(self, context):
        panel = AB_PT_asset_props_viewport
        try:
            bpy.utils.unregister_class(panel)
        except RuntimeError as e:
            report_message("ERROR", message=e)
            return
        if self.viewport_panel_category:
            panel.bl_region_type = "UI"
            panel.bl_category = self.viewport_panel_category
        else:
            panel.bl_region_type = "WINDOW"
            panel.bl_category = ""
        bpy.utils.register_class(panel)

    viewport_panel_category: StringProperty(
        name="3D Viewport panel category",
        description="The tab in the N-Panel to put the asset settings panel in (to disable it, set this to nothing: '')",
        default="Asset Bridge",
        update=viewport_panel_category_update,
    )

    def browser_panel_location_update(self, context):
        browser_panel = AB_PT_asset_info
        bpy.utils.unregister_class(browser_panel)
        browser_panel.bl_region_type = "TOOLS" if self.browser_panel_location == "LEFT" else "TOOL_PROPS"
        bpy.utils.register_class(browser_panel)

    browser_panel_location: EnumProperty(
        items=[
            ("LEFT", "Left hand side", "Draw the panel on the left hand side, underneath the category list"),
            ("RIGHT", "Right hand side", "Draw the panel on the right hand side, underneath the asset info panel"),
        ],
        name="Asset Browser Panel Location",
        default="LEFT",
        update=browser_panel_location_update,
    )

    auto_pack_files: BoolProperty(
        name="Automatically pack files",
        description="Automatically packed imported images into the current file,\
            meaning that if the source file is moved, they will still be accessible in the blend file.\
            This will result in larger files though.".replace(
            "  ", ""
        ),
        default=False,
    )

    widget_scale: FloatProperty(
        name="Download widget scale",
        description="The scale of the widget that shows the download progress of an asset in the 3D viewport",
        default=1.0,
        min=0,
        soft_min=0.1,
        soft_max=2,
        subtype="FACTOR",
    )

    widget_anim_speed: FloatProperty(
        name="animation speed",
        description="The speed of the animations for the download widget in the 3D viewport",
        default=1.0,
        min=0,
        soft_min=0.1,
        soft_max=2,
        subtype="FACTOR",
    )

    # IMPORT SETTINGS PANEL
    show_import_settings: new_show_prop("import", False)
    draw_import_settings_at_top: BoolProperty(
        name="Whether to show the import settings at the top of the panel or at the bottom",
        default=True,
    )
    show_asset_info: new_show_prop("asset", True)

    # SHOW PREFS SECTIONS
    show_general: new_show_prop("general")
    show_websites: new_show_prop("websites")
    show_contact: new_show_prop("contact")
    show_tasks: new_show_prop("tasks")
    show_updates: new_show_prop("tasks")

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

        box = layout.box().column(align=True)
        box.label(text="Library path:")
        row = box.row(align=True)
        row.scale_y = 1.5
        sub = row.row(align=True)
        InfoSnippets.lib_path.draw(sub)
        row.scale_x = 1.5
        row.prop(self, "lib_path", text="")
        if message := is_lib_path_invalid(self.lib_path):
            box.alert = True
            wrap_text(context, message, box)
            return

        ab = get_ab_settings(context)
        lists_obj = get_asset_lists()

        # Draw the download previews button/progress bar
        new_assets_available = lists_obj.new_assets_available()
        # Check if there are new assets/whether they are already downloading
        if PREVIEW_DOWNLOAD_TASK_NAME in ab.tasks.keys() or new_assets_available or not lists_obj.all_initialized:
            task = ab.tasks.get(PREVIEW_DOWNLOAD_TASK_NAME)
            if task and not task.progress:
                box = layout.box().column(align=True)
                box.label(text="Error with downloading previews, click here to reset:", icon="ERROR")
                box.separator()
                row = box.row(align=True)
                row.scale_y = 1.5
                op = AB_OT_remove_task.draw_button(row, text="Reset", icon="FILE_REFRESH")
                op.name = PREVIEW_DOWNLOAD_TASK_NAME
                return

            all_assets = lists_obj.all_assets
            preview_files = os.listdir(DIRS.previews)
            first_time = len(preview_files) == 0
            task_steps = task.progress.max if task else 0

            # Draw info showing the number of previews to download, only if it is not the first time download
            if new_assets_available and task_steps != len(all_assets) and not first_time:
                needed_previews = set(a.ab_idname for a in all_assets.values()) - {
                    p.replace(".png", "") for p in preview_files
                }
                layout.label(text=self.format_download_label(needed_previews))

            # Draw the button/progress bar
            draw_download_previews(layout, reload=first_time)
            return

        row = layout.box().row(align=True)
        row.scale_y = 1.5
        asset_lists = get_asset_lists()

        dummy_blends = [f for f in DIRS.dummy_assets.iterdir() if f.suffix == ".blend"]

        if (task := ab.tasks.get(CHECK_NEW_ASSETS_TASK_NAME)) and task.progress:
            task.draw_progress(row)

        elif len(dummy_blends) < len(asset_lists):
            InfoSnippets.set_up_dummy_assets.draw(row)
            row.scale_x = 1.5
            op = row.operator(
                AB_OT_check_for_new_assets.bl_idname,
                text="Check for new assets and set up asset library",
            )
            op.auto_download = True
            # AB_OT_create_dummy_assets.draw_button(row, text="Set up asset library")
            # AB_OT_create_dummy_assets.
            # print("ho")
            return

        else:
            op = row.operator_menu_hold(
                AB_OT_check_for_new_assets.bl_idname,
                icon="IMPORT",
                text="Check for new assets",
                menu=AB_MT_download_previews_menu.__name__,
            )
            op.bl_description = (
                "Check for new assets, and if they exist, download their previews and update the library."
            )

        grid = layout.grid_flow(row_major=True, even_columns=True)

        # GENERAL
        section = draw_prefs_section(grid, "General", self, "show_general")
        fac = 0.5
        draw_inline_prop(section, self, "auto_pack_files", "Auto pack files", "", factor=fac)
        draw_inline_prop(section, self, "viewport_panel_category", "N-Panel category", "", factor=fac)
        draw_inline_prop(section, self, "browser_panel_location", "Browser panel side", "", factor=fac)
        col = section.column(align=True)
        draw_inline_prop(col, self, "widget_scale", "Widget scale", "", factor=fac)
        draw_inline_prop(col, self, "widget_anim_speed", "Animation speed", "", factor=fac)
        col = draw_inline_column(col, "Open log file", factor=fac)
        AB_OT_open_log_file.draw_button(col, text="Open       ", icon="FILE_TICK")
        # AB_OT_open_log_file.draw_button(col, text="", icon="FILE_TICK")

        # WEBSITES
        section = draw_prefs_section(
            grid,
            "Asset websites",
            self,
            "show_websites",
        ).column(align=True)
        section.scale_y = section.scale_x = 1.5
        for asset_list in asset_lists.values():
            row = section.row(align=True)
            op = row.operator("wm.url_open", text=asset_list.label, icon_value=asset_list.icon)
            op.url = asset_list.url

            op = row.operator("wm.url_open", text="", icon="FUND")
            op.url = asset_list.support_url

        # CONTACT
        section = draw_prefs_section(grid, "Contact", self, "show_contact").column(align=True)
        section.scale_y = section.scale_x = 1.5

        op = section.operator("wm.url_open", text="Blender Artists        ", icon_value=ICONS.ab_blender_artists)
        op.url = "https://blenderartists.org/t/asset-bridge-addon/1397728?u=strike_digital"

        op = section.operator("wm.url_open", text="Blender Market        ", icon_value=ICONS.ab_blender_market)
        op.url = "https://blendermarket.com/creators/strike-digital"

        op = section.operator("wm.url_open", text="Twitter        ", icon_value=ICONS.ab_twitter)
        op.url = "https://twitter.com/StrikeDigital1"

        op = section.operator("wm.url_open", text="Leave a review :)        ", icon_value=ICONS.ab_review)
        op.url = "https://blendermarket.com/products/asset-bridge/ratings"

        section = draw_prefs_section(grid, "Auto updates", self, "show_updates").column(align=True)
        section.scale_y = 0.8
        draw_update_settings_ui(self, context, section)

        if __IS_DEV__ and self.show_tasks and len(ab.tasks):
            # Debug section showing the currently running tasks
            section = draw_prefs_section(grid, "Tasks", self, "show_tasks")
            section.scale_y = 0.7
            for task in ab.tasks:
                col = draw_inline_column(section, task.name, factor=0.5)
                row = col.row(align=True)
                row.label(text=f"Progress obj: {'Yes' if task.progress else 'No'}")
                op = AB_OT_remove_task.draw_button(row, text="", icon="X", emboss=False)
                op.name = task.name
                col.label(text=f"Finished: {task.finished}")
                col.label(text=f"Cancelled: {task.cancelled}")
                section.separator()


@BMenu()
class AB_MT_download_previews_menu(Menu):
    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.5
        op = AB_OT_download_previews.draw_button(layout, icon="FILE_REFRESH", text="Reload all assets")
        op.bl_description = "Redownload all previews and re setup the asset catalog again (good for debugging)"
        op.reload = True

        if __IS_DEV__:
            op = AB_OT_download_previews.draw_button(layout, icon="FILE_SCRIPT", text="Debug download")
            op.bl_description = "download a small subset of the assets, for speed"
            op.reload = True
            op.test_number = 100

            op = AB_OT_create_dummy_assets.draw_button(layout, icon="FILE_SCRIPT", text="Debug set-up library")
            op.bl_description = "Re-setup the asset library file"

        op = AB_OT_open_folder.draw_button(layout, text="Open previews folder", icon="FILE_FOLDER")
        op.bl_description = "Open the folder containing the preview files"
        op.file_path = str(DIRS.previews)


def register():
    # The panel locations need to be updated so that they don't just use the default value the next time the
    # addon is loaded.
    # Do this in a timer to have access to the context.
    def on_load():
        prefs = get_prefs(bpy.context)
        prefs.browser_panel_location_update(bpy.context)
        prefs.viewport_panel_category_update(bpy.context)

    bpy.app.timers.register(on_load)
