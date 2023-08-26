from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_dummy(BOperator.type):
    """Do nothing, sometimes useful for UI stuff."""

    def execute(self, context):
        pass
