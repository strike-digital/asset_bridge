import webbrowser

from bpy.props import StringProperty
from bpy.types import Operator

from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_open_folder(Operator):
    """Open a folder in the default file explorer"""

    file_path: StringProperty(
        default=".",
        description="The path to the folder to open. By default this is the addon folder",
    )

    def execute(self, context):
        webbrowser.open(self.file_path)
        return {"FINISHED"}