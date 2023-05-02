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
        message = self.message.replace("  ", "").replace("\n", " ")
        wrap_text(context, message, box, width=self.width * 1.25, splitter=" ")


@dataclass
class InfoSnippet():

    title: str
    message: str
    icon: str = "NONE"

    def draw(self, layout: UILayout, icon_override=""):
        op = layout.operator(AB_OT_show_info.bl_idname, text="", icon=icon_override or "INFO")
        op.title = self.title
        op.message = self.message
        op.icon = self.icon


class InfoSnippets():

    lib_path = InfoSnippet(
        "Lbrary path",
        """\
        This is the directory that all of the downloaded assets will be stored in.\n
        It's a good idea to make sure that this is somewhere that won't be change often, as if it is, and you \
        change/remove the directory, all of the blend files that the downloaded assets were used in won't be able to \
        find them, and will instead render with pink textures as placeholders.\n

        This doesn't apply if the 'auto pack files' setting is enabled, as this will store all of the assets inside \
        the blend file when they are imported, at the cost of the file size of the blend file being much larger. \
        """,
        icon="FILE_FOLDER",
    )

    set_up_dummy_assets = InfoSnippet(
        "Set up asset library",
        """\
        In order for the online assets to show up in the Blender asset browser, the addon first needs to set up \
        a blend file containing a bunch of dummy assets to represent them. As an example, the object assets are \
        just represented by empties, but their asset data is set to show up as if it is the online asset.\n
        
        This button simply creates a blend file containing these dummy assets that the addon can then use.
        """,
        icon="FILE_FOLDER",
    )

    displacement_unavailable = InfoSnippet(
        "Displacement unavailable",
        """\
        Material displacement is only available in Cycles.\n\n
        To get the best results, in Cycles set the feature set to 'Experimental' and add a new subdivision surface \
        modifier to the object you want to displace. Then enable the 'adaptive subdivision' checkbox, and in rendered view, \
        the parts of the mesh closest to the camera will have a very high quality subdivision, while parts far away \
        will have lower quality.\n
        
        This will give you the best looking displacement, but be aware that it can increase memory usage and render \
        initialization times substantially, so it's best to use sparingly unless you have a godly PC.
        """,
    )
