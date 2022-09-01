import json
import bpy
from os import walk
from pathlib import Path
import subprocess
from bpy.types import AddonPreferences, UILayout
from .operators import AB_OT_clear_asset_folder, AB_OT_set_prop
from .ui import AB_PT_browser_settings_panel, AB_PT_main_panel, draw_download_previews, draw_downloads_path
from .helpers import asset_preview_exists, update_prefs_file
from .constants import ASSET_LIB_VERSION, DIRS, FILES
from bpy.props import StringProperty, EnumProperty


class AddonPreferences(AddonPreferences):
    bl_idname = __package__
    layout: UILayout

    def lib_path_update(self, context):
        """Update all references to library paths"""

        update_prefs_file()

        path = Path(self.lib_path)
        if not path.exists():
            return
        DIRS.update(self.lib_path)
        ab = context.scene.asset_bridge.panel
        if ab.selected_asset:
            ab.selected_asset.update()

        # If old, update to the new blend file format
        if not FILES.lib_info.exists():
            for path, dirs, files in walk(DIRS.library):
                for file in files:
                    if file.endswith(".blend"):
                        subprocess.Popen([
                            bpy.app.binary_path,
                            Path(path) / file,
                            "--factory-startup",
                            "-b",
                            "--python",
                            FILES.setup_model_blend,
                        ])
            with open(FILES.lib_info, "w") as f:
                json.dump({"version": ASSET_LIB_VERSION}, f)

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

    def browser_panel_location_update(self, context):
        bpy.utils.unregister_class(AB_PT_browser_settings_panel)
        AB_PT_browser_settings_panel.bl_region_type = self.browser_panel_location
        bpy.utils.register_class(AB_PT_browser_settings_panel)

    browser_panel_location: EnumProperty(
        items=(
            ("TOOLS", "Left hand side", "Place the asset bridge panel on the left hand side of the asset browser"),
            ("TOOL_PROPS", "Right hand side",
             "Place the asset bridge panel on the right hand side of the asset browser"),
        ),
        name="Asset browser panel location:",
        update=browser_panel_location_update,
    )

    def viewport_panel_category_update(self, context):
        bpy.utils.unregister_class(AB_PT_main_panel)
        AB_PT_main_panel.bl_category = self.viewport_panel_category
        bpy.utils.register_class(AB_PT_main_panel)

    viewport_panel_category: StringProperty(
        name="Viewport panel category",
        description="The category in the N-panel of the 3D view in which to put the asset browser panel",
        update=viewport_panel_category_update,
        default="Asset Bridge")

    def draw(self, context):
        layout = self.layout
        ab = context.scene.asset_bridge.panel
        if not asset_preview_exists(ab.asset_name) or ab.preview_download_progress_active:
            draw_download_previews(layout)
            return

        if not draw_downloads_path(layout, context):
            return

        row = layout.box().row(align=True)
        row.scale_y = 1.5
        draw_download_previews(row, reload=True)
        row.operator(AB_OT_clear_asset_folder.bl_idname, icon="FILE_REFRESH")
        row.operator(
            "wm.url_open",
            icon="FUND",
            text="Support Polyhaven",
        ).url = "https://www.patreon.com/polyhaven/overview"
        if context.scene.asset_bridge.panel.import_progress_active:
            op: AB_OT_set_prop = row.operator(AB_OT_set_prop.bl_idname, text="Reset download progress")
            op.data_path = "context.scene.asset_bridge.panel"
            op.prop_name = "import_progress_active"
            op.value = "False"
            op.eval_value = True
            op.bl_description = "Reset the download progress bar in case of an error causing it to get stuck"

        box = layout.column(align=True)
        box1 = box.box()
        split = box1.split(align=True)
        split.label(text="Viewport panel category:")
        split.prop(self, "viewport_panel_category", text="")
        box1 = box.box()
        split = box1.split(align=True)
        split.label(text="Asset browser panel location:")
        split.prop(self, "browser_panel_location", text="")
        # box.use_property_split = True
        box.scale_y = 1.2
        # box.prop(self, "browser_panel_location")