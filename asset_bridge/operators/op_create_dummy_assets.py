import subprocess
from time import perf_counter
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
            print(asset_list_name)
            process = new_blender_process(
                Files.script_create_dummy_assets,
                script_args=["--asset_list", asset_list_name],
                use_stdout=False,
                # use_stdout=True,
            )
            processes[asset_list_name] = process

        start = perf_counter()
        update_interval = .01

        def output_log(name, process):
            try:
                out = process.stdout.read().decode()
            except AttributeError:
                out = "stdin not used"
            print(out)
            with open(DIRS.dummy_assets / f"{name}_log.txt", "w") as f:
                f.write(out)
            return out

        def check_processes():
            """Check all of the blender processes and get the progress from them"""

            # If cancel button is pressed
            if progress.cancelled:
                for name, process in processes.items():
                    process.kill()
                    output_log(name, process)
                report_message("Setup cancelled.", severity="INFO")
                return

            # Check if all processes are finished
            completed = True
            for process in processes.values():
                if process.poll() is None:
                    completed = False

            # Handle a time out if the process continues for more than 100 seconds. I really hope no ones computer is
            # Slow enough to run into this naturally, but oh well.
            # TODO: Make this a sensible number
            if perf_counter() - start > 20:
                completed = True
                for name, process in processes.items():
                    process.kill()
                    log = output_log(name, process)
                report_message(message=f"Process timed out, please try again.\nError log:\n{log}", severity="ERROR")

            if completed:

                catalog = AssetCatalogFile(DIRS.dummy_assets)
                catalog.reset()
                for name in processes:
                    file = DIRS.dummy_assets / f"{name}.cats.txt"
                    if not file.exists():
                        task.finish()
                        raise FileExistsError(f"Cannot open catalog file {file}")
                    other_catalog = AssetCatalogFile(DIRS.dummy_assets, f"{name}.cats.txt")
                    catalog.merge(other_catalog)
                catalog.write()

                # Handle any errors
                errors = False
                for name, process in processes.items():
                    out = output_log(name, process)
                    if "Error" in out:
                        report_message(f"Error creating assets for {name}:\n{out}", severity="ERROR")
                        errors = True

                if not errors:
                    report_message(
                        f"Downloaded and setup {progress.max} assets in {perf_counter() - task.start_time:.2f}s",
                        severity="INFO",
                    )

                task.finish()
                force_ui_update(area_types={"PREFERENCES"})
                return

            # File hasn't been created yet
            if not FILES.lib_progress.exists():
                return update_interval

            # Update progress
            total = 0
            for name in processes:
                file = DIRS.dummy_assets / f"{name}_progress.txt"
                if not file.exists():
                    continue
                with open(file, "r") as f:
                    try:
                        total += int(f.read())
                    except ValueError:
                        return update_interval
            progress.progress = total

            return update_interval

        bpy.app.timers.register(check_processes)
        return {"FINISHED"}
