from threading import Thread
import bpy
from ..api import get_asset_lists
from bpy.props import BoolProperty
from bpy.types import Operator
from ..btypes import BOperator


@BOperator("asset_bridge", label="Get asset lists.")
class AB_OT_initialize_asset_lists(Operator):
    """Re initialize all asset lists with data from the internet rather than from the cache"""

    initialize_all: BoolProperty(default=False)

    def execute(self, context):
        lists_obj = get_asset_lists()
        asset_lists = lists_obj.asset_lists

        if self.initialize_all:
            lists_obj.initialize_all()
        else:
            threads = []
            for asset_list in asset_lists:
                if not lists_obj.is_initialized(asset_list):
                    thread = Thread(target=lists_obj.initialize_asset_list, args=[asset_list])
                    thread.start()
                    threads.append(thread)
            for thread in threads:
                thread.join()

        bpy.ops.asset_bridge.download_previews()
        return {"FINISHED"}