from bpy.props import StringProperty
from bpy.types import Operator
from ..btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_swap_asset(Operator):

    to_quality: StringProperty()

    asset_type: StringProperty(description="The type of asset that should be swapped")

    data_block_name: StringProperty(description="The name of the data block to be swapped (e.g. World, Object, etc.)")

    def execute(self, context):
        print("Swap")
        return {"FINISHED"}
