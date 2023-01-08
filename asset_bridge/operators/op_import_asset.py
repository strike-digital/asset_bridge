import os
from threading import Thread

from ..helpers.process import format_traceback

from ..helpers.library import get_dir_size

from .op_report_message import report_message

import bpy

from ..btypes import BOperator
from ..api import get_asset_lists
from ..settings import get_ab_settings, get_asset_settings
from ..helpers.main_thread import force_ui_update, run_in_main_thread
from ..helpers.drawing import get_active_window_region, point_under_mouse
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty, StringProperty
from bpy.types import Collection, Material, Object, Operator
from mathutils import Vector as V


@BOperator("asset_bridge")
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

    location: FloatVectorProperty(
        description="The location to put the imported asset/where to draw the progress",
        default=(0, 0, 0),
    )

    at_mouse: BoolProperty(
        description="Whether to import the asset at the point underneath the mouse cursor, or instead at the 3d cursor",
        default=False,
    )

    link_method: EnumProperty(
        items=[
            ("LINK", "Link", "Link"),
            ("APPEND", "Append", "Append"),
            ("APPEND_REUSE", "Append reuse", "Append reuse"),
        ],
        default="APPEND_REUSE",
    )

    material_slot = None

    def invoke(self, context, event):
        # This is the best way I know to be able to pass custom data to operators
        self.material_slot = self.__class__.material_slot
        self.__class__.material_slot = None

        # Store mouse positions
        self.mouse_pos_region = V((event.mouse_region_x, event.mouse_region_y))
        self.mouse_pos_window = V((event.mouse_x, event.mouse_y))
        return self.execute(context)

    def execute(self, context):

        if self.at_mouse:
            # Get the position of the mouse in 3D space
            if context.region:
                region = context.region
                coord = self.mouse_pos_region
            else:
                region = get_active_window_region(self.mouse_pos_window, fallback_area_type="VIEW_3D")
                coord = self.mouse_pos_window - V((region.x, region.y))
                # TODO: Try and fix this
                if not region or any(c < 0 for c in coord):
                    message = "Cannot import assets when another blender window is active"
                    report_message(message, "ERROR")
                    return {"CANCELLED"}

            location = point_under_mouse(context, region, coord)
        else:
            location = V(self.location)

        ab = get_ab_settings(context)
        asset_list_item = get_asset_lists().all_assets[self.asset_name]
        asset = asset_list_item.to_asset(self.asset_quality, self.link_method)
        files = asset.get_files()

        # These need to variables rather than instance attributes so that they
        # can be accesed in another thread after the operator has finished.
        material_slot = self.material_slot
        quality = self.asset_quality

        # Download the asset in a separate thread to avoid locking the interface,
        # and then import the asset in the main thread again to avoid errors.
        def download_and_import_asset():

            if not asset_list_item.is_downloaded(quality) or ab.reload_asset:
                max_size = asset.get_download_size(quality)
                task = ab.new_task()
                task.new_progress(max_size)

                # Delete existing files
                for file in files:
                    os.remove(file)

                # Run the draw operator
                run_in_main_thread(
                    bpy.ops.asset_bridge.draw_import_progress,
                    args=["INVOKE_DEFAULT"],
                    kwargs={
                        "task_name": task.name,
                        "location": location
                    },
                )

                def check_progress():
                    """Check to total file size of the downloading files, and update the progress accordingly"""
                    if task.progress:
                        orig_progress = task.progress.progress
                        if (size := get_dir_size(asset.download_dir)) != orig_progress:
                            task.progress.progress = size
                            force_ui_update(area_types="VIEW_3D")
                        return .01
                    return None

                # Download the asset
                bpy.app.timers.register(check_progress)
                try:
                    asset.download_asset()
                except Exception as e:
                    report_message(
                        f"Error downloading asset {asset.idname}:\n{format_traceback(e)}",
                        severity="ERROR",
                        main_thread=True,
                    )
                force_ui_update(area_types="VIEW_3D")
                task.finish()

            def import_asset():
                try:
                    imported = asset.import_asset(context)

                    def update_settings(data_block):
                        settings = get_asset_settings(data_block)
                        settings.is_asset_bridge = True
                        settings.idname = asset_list_item.idname

                    if isinstance(imported, Material):
                        update_settings(imported)
                        if material_slot:
                            material_slot.material = imported
                    elif isinstance(imported, Object):
                        update_settings(imported)
                        imported.location += location
                    elif isinstance(imported, Collection):
                        for obj in imported.objects:
                            update_settings(obj)
                            obj.location += location
                except Exception as e:
                    report_message(f"Error importing asset {asset.idname}:\n{format_traceback(e)}", severity="ERROR")

            # This is modifying blender data, so needs to be run in the main thread
            run_in_main_thread(import_asset)

        thread = Thread(target=download_and_import_asset)
        thread.start()

        # Blender is weird, and without executing this in a timer, all imported objects will be
        # scaled to zero after execution. God knows why.
        return {"FINISHED"}