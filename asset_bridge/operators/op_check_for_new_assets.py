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

    def execute(self, context):
        lists_obj = get_asset_lists()
        threads = lists_obj.initialize_all(blocking=False)
        task = get_ab_settings(context).new_task(name=CHECK_NEW_ASSETS_TASK_NAME)
        task.new_progress(max_steps=len(threads))

        def finish():
            if task.cancelled:
                report_message("Cancelled checking for new assets")
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
                suffix = "s" if new_assets > 1 else ""
                are = "are" if new_assets > 1 else "is"
                if self.report_message:
                    report_message(f"There {are} {new_assets} new asset{suffix} to download.", "INFO")
            elif self.report_message:
                report_message("No new assets found, you're up to date!")

            force_ui_update(area_types={"PREFERENCES"})

        bpy.app.timers.register(finish)
        return {"FINISHED"}