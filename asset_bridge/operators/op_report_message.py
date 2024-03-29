from functools import wraps

from bpy.props import StringProperty

from ..helpers.btypes import BOperator, ExecContext
from ..helpers.main_thread import run_in_main_thread
from ..helpers.process import format_traceback


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
        return self.RUNNING_MODAL

    def modal(self, context, event):
        context.window_manager.event_timer_remove(self.timer)
        self.report({self.severity}, self.message)
        return self.FINISHED


def report_message(severity="INFO", message="Message!", main_thread=False):
    if main_thread:
        run_in_main_thread(report_message, (severity, message, False))
    else:
        AB_OT_report_message.run(ExecContext.INVOKE, severity=severity, message=str(message))


def report_exceptions(main_thread=False):
    """A decorator to automatically report exceptions in the UI, useful when working with separate threads."""
    def report_exceptions_decorator(func):
        @wraps(func)
        def with_reporting(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                report_message(
                    "ERROR",
                    f"An error occurred while executing function {func.__name__}:\n\n{format_traceback(e)}",
                    main_thread=main_thread,
                )
        return with_reporting
    return report_exceptions_decorator
