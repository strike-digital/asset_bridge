
from ..helpers.main_thread import run_in_main_thread
import bpy
from ..btypes import BOperator
from bpy.types import Operator
from bpy.props import StringProperty


@BOperator("asset_bridge")
class AB_OT_report_message(Operator):
    """Report a message at the bottom of th screen, and in the info editor.
    Useful for threads and scripts that aren't being executed inside operators"""

    severity: StringProperty(default="INFO")

    message: StringProperty(default="")

    def invoke(self, context, event):
        """The report needs to be done in the modal function otherwise it wont show at the bottom of the screen
        for some reason ¯\_(ツ)_/¯"""  # noqa
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        self.report({self.severity}, self.message)
        return {"FINISHED"}


def report_message(message="Message!", severity="INFO", main_thread=False):
    if main_thread:
        run_in_main_thread(report_message, (message, severity, False))
    else:
        bpy.ops.asset_bridge.report_message("INVOKE_DEFAULT", message=message, severity=severity)