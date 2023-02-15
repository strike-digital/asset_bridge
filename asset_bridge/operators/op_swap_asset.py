from bpy.props import StringProperty
from bpy.types import Operator

from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_swap_asset(Operator):

    to_quality: StringProperty()

    asset_id: StringProperty(description="The identifier of the asset to be swapped")

    def execute(self, context):
        print(self.to_quality, self.asset_id)
        print("Swap")
        print(context.region.type)
        return {"FINISHED"}
