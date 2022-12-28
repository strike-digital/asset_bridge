
from ..settings import AssetBridgeSettings
from ..btypes import BOperator
from bpy.types import Operator
from ..api import get_apis


@BOperator("asset_bridge")
class AB_OT_create_dummy_assets(Operator):
    """Create the dummy assets representing each online asset"""

    def execute(self, context):
        ab: AssetBridgeSettings = context.window_manager.asset_bridge
        assets = get_apis().all_assets
        print(assets)

        return {"FINISHED"}
