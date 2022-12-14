from bpy.props import BoolProperty
from .op_report_message import report_message
from ..api import get_asset_lists
from bpy.types import Operator
from ..btypes import BOperator


@BOperator("asset_bridge", label="Check for new assets")
class AB_OT_check_for_new_assets(Operator):
    """Re download the asset lists and check for new assets"""

    report_message: BoolProperty(default=True)

    def execute(self, context):
        lists_obj = get_asset_lists()
        lists_obj.initialize_all()
        new_assets = lists_obj.new_assets_available()
        if new_assets:
            suffix = "s" if new_assets > 1 else ""
            are = "are" if new_assets > 1 else "is"
            if self.report_message:
                report_message(f"There {are} {new_assets} new asset{suffix} to download.", "INFO")
        elif self.report_message:
            report_message("No new assets found, you're up to date!")
        return {"FINISHED"}