
from ..settings import get_ab_settings
from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_clear_task(BOperator.type):
    """Clear all Asset Bridge tasks"""

    def execute(self, context):
        ab = get_ab_settings(context)
        for task in ab.tasks:
            task.finish(remove=True)
        return {"FINISHED"}
