from dataclasses import dataclass

from bpy.props import IntProperty, BoolProperty, StringProperty
from bpy.types import Operator, UILayout

from ..ui.ui_helpers import wrap_text
from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_show_info(Operator):

    title: StringProperty()

    message: StringProperty()

    icon: StringProperty()

    show_content: BoolProperty()

    width: IntProperty(default=300)

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=self.width)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        box = column.box().row(align=True)
        box.alignment = "CENTER"
        offset = "" if self.icon else "    "
        box.label(text=self.title + offset, icon=self.icon)

        box = column.box().column(align=True)
        # box.alignment = "CENTER"
        message = self.message.replace("  ", "").replace("\n", " ")
        wrap_text(context, message, box, width=self.width * 1.25, splitter=" ")


@dataclass
class InfoSnippet():

    title: str
    message: str
    icon: str = "NONE"

    def draw(self, layout: UILayout):
        op = layout.operator(AB_OT_show_info.bl_idname, text="", icon="INFO")
        op.title = self.title
        op.message = self.message
        op.icon = self.icon


class InfoSnippets():

    lib_path = InfoSnippet(
        "Lbrary path",
        """\
        This is the directory that all of the downloaded assets will be stored in.\n
        It's a good idea to make sure that this is somewhere that won't be change often, as if it is, and you\
        change/remove the directory, all of the blend files that the downloaded assets were used in won't be able to\
        find them, and will instead render with pink textures as placeholders.\n

        This doesn't apply if the 'auto pack files' setting is enabled, as this will store all of the assets inside\
        the blend file when they are imported, at the cost of the file size of the blend file being much larger.\
        """,
        icon="FILE_FOLDER",
    )


INFO = InfoSnippets()