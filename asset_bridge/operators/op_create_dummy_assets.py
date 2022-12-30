import json
import subprocess
from threading import Thread
from time import perf_counter, sleep
from typing import Dict

from ..helpers.main_thread import force_ui_update

from ..settings import get_ab_settings

from ..helpers.library import ensure_bl_asset_library_exists
from .op_report_message import report_message
import bpy
from ..catalog import AssetCatalogFile
from ..constants import DIRS, FILES, PREVIEW_DOWNLOAD_TASK_NAME, Files
from ..helpers.process import new_blender_process
from ..btypes import BOperator
from ..api import get_asset_lists
from bpy.types import Operator

last_messages = {}
process_progress = {}


@BOperator("asset_bridge")
class AB_OT_create_dummy_assets(Operator):
    """Create the dummy assets representing each online asset"""

    def execute(self, context):
        asset_lists = get_asset_lists()
        ensure_bl_asset_library_exists()
        catalog = AssetCatalogFile(DIRS.dummy_assets)
        catalog.reset()

        # Update/create the progress bar
        ab = get_ab_settings(context)
        task = ab.tasks.get(PREVIEW_DOWNLOAD_TASK_NAME)
        if not task:
            task = ab.new_task(PREVIEW_DOWNLOAD_TASK_NAME)
        progress = task.new_progress(max_steps=len(asset_lists.all_assets))
        progress.progress = 0
        force_ui_update(context.area)
        progress.message = ("(2/2) Setting up asset library:")

        # Create a blender process for each asset list
        processes: Dict[str, subprocess.Popen] = {}
        for asset_list_name in asset_lists.keys():
            process = new_blender_process(
                Files.script_create_dummy_assets,
                script_args=["--asset_list", asset_list_name],
            )
            processes[asset_list_name] = process
        start = perf_counter()

        update_interval = .01

        def check_processes():
            completed = True

            for process in processes.values():
                if process.poll() is None:
                    completed = False

            if perf_counter() - start > 100:
                completed = True
                for process in processes.values():
                    process.kill()
                report_message(message="Process timed out, please try again", severity="ERROR")

            if completed:
                task.finish()
                force_ui_update(area_types={"PREFERENCES"})
                return

            if not FILES.lib_progress.exists():
                return update_interval

            with open(FILES.lib_progress, "r") as f:
                try:
                    contents = json.load(f)
                except json.JSONDecodeError:
                    sleep(.1)
                    return update_interval

            progress.progress = sum(contents.values())

            return update_interval

        bpy.app.timers.register(check_processes)
        return {"FINISHED"}
