import os
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from .constants import BL_ASSET_LIB_NAME, DOWNLOADS_DIR, FILES, FILES_RELATIVE
from .helpers import Asset, Op, asset_list, ensure_asset_library
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
        print("Importing:", ab.asset_name)
        return {'FINISHED'}


@Op("asset_bridge", undo=True)
class AB_OT_clear_asset_folder(Operator):

    def execute(self, context):
        downloads = DOWNLOADS_DIR
        for dirpath, dirnames, file_names in os.walk(downloads):
            for file in file_names:
                if file.split(".")[-1] not in ["jpg", "jpeg", "png", "hdr", "blend", "blend1", "exr"]:
                    continue
                os.remove(os.path.join(dirpath, file))
        return {'FINISHED'}


@Op("asset_bridge", undo=True)
class AB_OT_report_message(Operator):

    severity: StringProperty(default="INFO")

    message: StringProperty(default="")

    def invoke(self, context, event):
        """The report needs to be done in the modal function otherwise it wont show at the bottom of the screen.
        For some reason ¯\_(ツ)_/¯"""  # noqa
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        self.report({self.severity}, self.message)
        return {"FINISHED"}


@Op("asset_bridge", undo=True)
class AB_OT_download_asset_previews(Operator):

    def execute(self, context):
        asset_list.update()
        thread = Thread(target=asset_list.download_all_previews, args=[False])
        thread.start()
        # asset_list.download_all_previews(reload=False)
        # subprocess.run([
        #     bpy.app.binary_path,
        #     # FILES["asset_lib_blend"],
        #     "--factory-startup",
        #     "-b",
        #     "--python",
        #     f'{FILES_RELATIVE["setup_asset_library"]}',
        # ])

        # ensure_asset_library()

        return {'FINISHED'}