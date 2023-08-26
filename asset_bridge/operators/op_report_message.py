from bpy.props import StringProperty

from ..helpers.btypes import BOperator, ExecContext
from ..helpers.main_thread import run_in_main_thread


@BOperator("asset_bridge")
class AB_OT_report_message(BOperator.type):
    """Report a message at the bottom of the screen, and in the info editor.
    Useful for threads and scripts that aren't being executed inside operators"""

    severity: StringProperty(default="INFO")

    message: StringProperty(default="")

    def invoke(self, context, event):
        """The report needs to be done in the modal function otherwise it wont show at the bottom of the screen
        for some reason ¯\_(ツ)_/¯"""  # noqa
        # We also need to add a timer to update the window to make sure that it shows up immediately,
        # rather than when the user moves their mouse.
        self.timer = context.window_manager.event_timer_add(0.001, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.window_manager.event_timer_remove(self.timer)
        self.report({self.severity}, self.message)
        return {"FINISHED"}


def report_message(severity="INFO", message="Message!", main_thread=False):
    if main_thread:
        run_in_main_thread(report_message, (severity, message, False))
    else:
        AB_OT_report_message.run(ExecContext.INVOKE, severity=severity, message=str(message))
