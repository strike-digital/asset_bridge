from bpy.types import Operator
from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_dummy(Operator):
    """Do nothing, sometimes useful for UI stuff."""