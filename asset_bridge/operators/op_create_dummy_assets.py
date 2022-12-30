from ..constants import Files
from ..helpers.process import new_blender_process
from ..btypes import BOperator
from ..api import get_asset_lists
from bpy.types import Operator


@BOperator("asset_bridge")
class AB_OT_create_dummy_assets(Operator):
    """Create the dummy assets representing each online asset"""

    def execute(self, context):
        asset_lists = get_asset_lists()
        for asset_list_name in asset_lists.keys():
            process = new_blender_process(
                Files.script_create_dummy_assets,
                script_args=["--asset_list", asset_list_name],
            )

        return {"FINISHED"}
