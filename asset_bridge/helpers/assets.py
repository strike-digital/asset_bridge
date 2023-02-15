import os
from threading import Thread

from .process import format_traceback
from .library import get_dir_size

import bpy

from .main_thread import force_ui_update, run_in_main_thread
from ..operators.op_report_message import report_message
from ..api import get_asset_lists
from ..apis.asset_types import Asset
from bpy.types import Context
from mathutils import Vector as V
from ..settings import get_ab_settings


def download_asset(
        context: Context,
        asset: Asset,
        draw: bool = True,
        location: V = V(),
) -> str:

    ab = get_ab_settings(context)
    all_assets = get_asset_lists().all_assets
    asset_list_item = asset.list_item

    # Handle if the asset is not in the list. Could happen if list is still loading for some reason, but is unlikely
    if not asset_list_item:
        report_message(
            f"Could not find asset {asset_list_item.label} in the asset list (Number of assets: {len(all_assets)})",
            "ERROR",
        )
        task = ab.new_task()
        task.cancel()
        return task.name

    elif message := asset_list_item.poll():
        report_message(message, "ERROR")
        task = ab.new_task()
        task.cancel()
        return task.name

    elif asset.is_downloaded() and not ab.reload_asset:
        task = ab.new_task()
        task.finish()
        return task.name

    ab = get_ab_settings(context)
    asset
    max_size = asset.get_download_size(quality_level)
    task = ab.new_task()
    task.new_progress(max_size)
    task_name = task.name

    # Delete existing files
    for file in asset.get_files():
        os.remove(file)

    if draw:
        # Run the draw operator
        bpy.ops.asset_bridge.draw_import_progress("INVOKE_DEFAULT", task_name=task.name, location=location)
        # run_in_main_thread(
        #     bpy.ops.asset_bridge.draw_import_progress,
        #     args=["INVOKE_DEFAULT"],
        #     kwargs={
        #         "task_name": task.name,
        #         "location": location
        #     },
        # )

    def download():

        def check_progress():
            """Check to total file size of the downloading files, and update the progress accordingly"""
            # Blender moves memory around a lot so it's best to get a new reference to the task each time.
            # Otherwise it causes errors when importing multiple assets at once.
            task = ab.tasks.get(task_name)
            if not task:
                return None
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

        task = ab.tasks[task_name]
        force_ui_update(area_types="VIEW_3D")
        run_in_main_thread(task.finish)

    thread = Thread(target=download)
    thread.start()

    return task.name
