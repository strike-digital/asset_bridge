from subprocess import Popen

from ..constants import Files
from ..helpers.process import new_blender_process
from ..settings import get_ab_settings
from ..btypes import BOperator
from bpy.types import Operator
from ..api import get_asset_lists


@BOperator("asset_bridge")
class AB_OT_create_dummy_assets(Operator):
    """Create the dummy assets representing each online asset"""

    def execute(self, context):
        ab = get_ab_settings(context)
        assets = get_asset_lists().all_assets
        process = new_blender_process(Files.script_create_dummy_assets)
        print(process.poll())
        Popen
        print(len(assets))

        return {"FINISHED"}
