from ..settings import AssetTask, get_ab_settings
from ..btypes import BOperator
from bpy.types import Operator
from bpy.props import StringProperty


@BOperator("asset_bridge")
class AB_OT_cancel_task(Operator):
    """Cancel an Asset Bridge task"""

    name: StringProperty()

    def execute(self, context):
        if not self.name:
            raise ValueError("No task name specified")

        ab = get_ab_settings(context)
        task: AssetTask = ab.tasks[self.name]
        if not task.progress:
            raise ValueError(f"Task '{self.name}' has no progress")

        task.progress.cancel()
        task.finish()
        return {"FINISHED"}