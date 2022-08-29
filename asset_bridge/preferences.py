import json
import bpy
from os import walk
from pathlib import Path
import subprocess
from bpy.types import AddonPreferences, UILayout
from .operators import AB_OT_clear_asset_folder, AB_OT_set_prop
from .ui import draw_download_previews, draw_downloads_path
from .helpers import asset_preview_exists, update_prefs_file
from .constants import ASSET_LIB_VERSION, DIRS, FILES
from bpy.props import StringProperty


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
        ab = context.scene.asset_bridge
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

    def draw(self, context):
        layout = self.layout
        ab = context.scene.asset_bridge
        if not asset_preview_exists(ab.asset_name) or ab.download_status == "DOWNLOADING_PREVIEWS":
            draw_download_previews(layout)
            return

        if not draw_downloads_path(layout, context):
            return
        # col = layout.box().column(align=True)
        # col.label(text="External Downloads Path:")
        # # col.scale_y = .5
        # row = col.row(align=True)
        # row.scale_y = row.scale_x = 1.5
        # path = Path(self.lib_path)
        # if not DIRS.is_valid:
        #     row.alert = True
        #     row.prop(self, "lib_path", text="")
        #     row2 = col.row(align=True)
        #     row2.alert = True
        #     row2.label(text="The given path is not valid")
        #     return
        # row.prop(self, "lib_path", text="")

        row = layout.box().row(align=True)
        row.scale_y = 1.5
        draw_download_previews(row, reload=True)
        row.operator(AB_OT_clear_asset_folder.bl_idname, icon="FILE_REFRESH")
        row.operator(
            "wm.url_open",
            icon="FUND",
            text="Support Polyhaven",
        ).url = "https://www.patreon.com/polyhaven/overview"
        if context.scene.asset_bridge.download_status != "NONE":
            op: AB_OT_set_prop = row.operator(AB_OT_set_prop.bl_idname, text="Reset download progress")
            op.data_path = "context.scene.asset_bridge"
            op.prop_name = "download_status"
            op.value = "NONE"
            op.eval_value = False
            op.bl_description = "Reset the download progress bar in case of an error causing it to get stuck"