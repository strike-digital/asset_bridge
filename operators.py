import os
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from .constants import DOWNLOADS_DIR, FILES, FILES_RELATIVE
from .helpers import Asset, Op, asset_list
from threading import Thread
import subprocess


@Op("asset_bridge", undo=True)
class AB_OT_import_asset(Operator):

    asset_name: StringProperty(
        description="The name of the asset to import. Leave empty to import the currently selected asset",
        default="",
    )

    asset_quality: StringProperty(
        description="The quality of the asset to import. Leave empty to import the currently selected asset quality",
        default="",
    )

    reload: BoolProperty(
        description="Whether to redownload the asset, or to use the local version if it is available.",
        default=False,
    )

    def execute(self, context):
        ab = context.scene.asset_bridge
        asset = Asset(self.asset_name if self.asset_name else ab.asset_name)
        self.__class__.asset = asset
        quality = self.asset_quality if self.asset_quality else ab.asset_quality
        thread = Thread(target=asset.import_asset, args=(context, quality, self.reload))
        thread.start()
        for area in context.screen.areas:
            for region in area.regions:
                region.tag_redraw()
        # asset.import_asset(context, quality=quality, reload=self.reload)
        print("Importing:", ab.asset_name)
        return {'FINISHED'}


@Op("asset_bridge", undo=True)
class AB_OT_clear_asset_folder(Operator):

    def execute(self, context):
        downloads = DOWNLOADS_DIR
        for dirpath, dirnames, file_names in os.walk(downloads):
            for file in file_names:
                if file.split(".")[-1] not in [".jpg", ".jpeg", ".png", ".hdr", ".blend", ".blend1", ".exr"]:
                    continue
                os.remove(os.path.join(dirpath, file))
        return {'FINISHED'}


@Op("asset_bridge", undo=True)
class AB_OT_check_for_new_assets(Operator):

    def execute(self, context):
        asset_list.download_all_previews(reload=False)
        subprocess.run([
            bpy.app.binary_path,
            FILES["asset_lib_blend"],
            "--factory-startup",
            "-b",
            "--python",
            f'{FILES_RELATIVE["setup_asset_library"]}',
        ])
        return {'FINISHED'}