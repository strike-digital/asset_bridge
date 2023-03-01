from ..helpers.general import check_internet
import bpy
from bpy.props import BoolProperty
from bpy.types import Operator

from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..constants import CHECK_NEW_ASSETS_TASK_NAME
from ..helpers.btypes import BOperator
from .op_report_message import report_message
from ..helpers.main_thread import force_ui_update


@BOperator("asset_bridge", label="Check for new assets")
class AB_OT_check_for_new_assets(Operator):
    """Re download the asset lists and check for new assets"""

    report_message: BoolProperty(default=True)

    auto_download: BoolProperty(default=False, description="Whether to automatically download newly found previews")

    def execute(self, context):

        if not check_internet():
            report_message("ERROR", "Can't check for new assets, no internet connection detected")
            return {"CANCELLED"}

        lists_obj = get_asset_lists()
        threads = lists_obj.initialize_all(blocking=False)
        task = get_ab_settings(context).new_task(name=CHECK_NEW_ASSETS_TASK_NAME)
        task.new_progress(max_steps=len(threads))

        def finish():
            if task.cancelled:
                report_message("INFO", "Cancelled checking for new assets")
                task.finish()
                return

            finished = 0
            for thread in threads:
                if not thread.is_alive():
                    finished += 1

            if finished < len(threads):
                alive = [t for t in threads if t.is_alive()]
                label = get_asset_lists()[alive[0].name].label
                task.update_progress(
                    finished,
                    message=f"Getting asset list from {label} ({finished + 1}/{len(threads)})",
                )
                return .1

            task.finish()
            new_assets = lists_obj.new_assets_available()
            if new_assets:
                if self.report_message:
                    suffix = "s" if new_assets > 1 else ""
                    are = "are" if new_assets > 1 else "is"
                    report_message("INFO", f"There {are} {new_assets} new asset{suffix} to download.")
                    if self.auto_download:
                        print("Auto download")
                        bpy.ops.asset_bridge.download_previews()
            else:
                if self.report_message:
                    report_message("INFO", "No new assets found, you're up to date!")
                if self.auto_download:
                    bpy.ops.asset_bridge.create_dummy_assets()

            force_ui_update(area_types={"PREFERENCES"})

        bpy.app.timers.register(finish)
        return {"FINISHED"}