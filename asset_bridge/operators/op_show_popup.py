from bpy.props import IntProperty, BoolProperty, EnumProperty, StringProperty
from bpy.utils import register_class, unregister_class

from ..ui.ui_helpers import wrap_text
from ..helpers.btypes import BOperator, ExecContext
from ..helpers.main_thread import run_in_main_thread


@BOperator("asset_bridge")
class AB_OT_show_popup(BOperator.type):
    """Show a popup with the given message to the user"""

    severity: EnumProperty(
        items=[
            ("INFO", "Info", "Normal text"),
            ("WARNING", "Warning", "Red text"),
        ],
        default="INFO",
    )

    message: StringProperty(default="")

    title: StringProperty(default="")

    width: IntProperty(default=300)

    centered: BoolProperty(default=True)

    confirm: BoolProperty(default=False, description="Show a confirm button at the bottom of the popup")

    # TODO: Implement this
    confirm_op: StringProperty(default="")

    # Function to call when the confirm button is clicked
    confirm_func = None

    def invoke(self, context, event):
        # Since we can't pass functions directly to operators, use a class variable,
        # and reset it as soon as the operator is called
        self.confirm_func = self.__class__.confirm_func
        self.__class__.confirm_func = None

        if self.confirm:
            return context.window_manager.invoke_props_dialog(self, width=self.width)

        return context.window_manager.invoke_popup(self, width=self.width)

    def draw(self, context):
        layout = self.layout
        layout.alert = self.severity != "INFO"

        col = layout.column(align=True)
        box = col.box().column(align=True)
        if self.title and not self.confirm:
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text=self.title)
            box = col.box().column(align=True)

        box.scale_y = 0.8
        wrap_text(context, self.message, box, centered=self.centered, width=self.width + 100)

    def execute(self, context):
        if self.confirm_func:
            self.confirm_func()
        return {"FINISHED"}


def show_popup(
    message="Message!",
    severity="INFO",
    title="",
    width=300,
    centered=True,
    confirm=False,
    confirm_op="",
    confirm_func=None,
    main_thread=False,
):
    if main_thread:
        run_in_main_thread(show_popup, (message, severity, False))
    else:
        if title and confirm:
            # Show the correct title in the topbar
            unregister_class(AB_OT_show_popup)
            AB_OT_show_popup.bl_label = title
            register_class(AB_OT_show_popup)

        if confirm_func:
            AB_OT_show_popup.confirm_func = confirm_func

        AB_OT_show_popup.run(
            ExecContext.INVOKE,
            message=message,
            severity=severity,
            title=title,
            width=width,
            centered=centered,
            confirm=confirm,
            confirm_op=confirm_op,
        )
