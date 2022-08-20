from pathlib import Path
from bpy.types import AddonPreferences, UILayout
from .operators import AB_OT_clear_asset_folder, AB_OT_set_prop
from .ui import draw_download_previews
from .helpers import asset_preview_exists
from .constants import DIRS
from bpy.props import StringProperty


class AddonPreferences(AddonPreferences):
    bl_idname = __package__
    layout: UILayout

    def lib_path_update(self, context):
        """Update all references to library paths"""
        path = Path(self.lib_path)
        if not path.exists():
            return
        DIRS.update(self.lib_path)
        ab = context.scene.asset_bridge
        if ab.selected_asset:
            ab.selected_asset.update()

    lib_path: StringProperty(
        name="External Downloads path",
        description="The path in which to save the downloaded assets. If left blank, the addon directory is used.\n\
            However, this is not ideal, as you will lose all downloaded assets if you upgrade or remove the addon.\n\
            As such, it's reccommended that you select\
            a directory that won't be moved in the future".replace("            ", ""),
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

        row = layout.row(align=True)
        row.scale_y = row.scale_x = 1.5
        split = row.split(align=True, factor=.3)
        path = Path(self.lib_path)
        if not path.exists():
            row.alert = True
            row2 = layout.row(align=True)
            row2.alert = True
            row2.label(text="The given path does not exist")
        row.prop(self, "lib_path")
        layout
        row = layout.row(align=True)
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