from ..apis.asset_utils import HDRI, MATERIAL
from .op_report_message import report_message
from bpy.props import (BoolProperty, EnumProperty, StringProperty, FloatVectorProperty)
from bpy.types import Operator
from mathutils import Vector as V

from ..api import get_asset_lists
from ..helpers.assets import download_and_import_asset
from ..helpers.btypes import BOperator
from ..helpers.drawing import point_under_mouse


@BOperator("asset_bridge")
class AB_OT_import_asset(Operator):

    asset_name: StringProperty(
        description="The name of the asset to import. Leave empty to import the currently selected asset",
        default="",
    )

    asset_quality: StringProperty(
        description="The quality of the asset to import. Leave empty to import the currently selected asset quality",
        default="",
    )

    reload: BoolProperty(
        description="Whether to redownload the asset, or to use the local version if it is available.",
        default=False,
    )

    location: FloatVectorProperty(
        description="The location to put the imported asset/where to draw the progress",
        default=(0, 0, 0),
    )

    at_mouse: BoolProperty(
        description="Whether to import the asset at the point underneath the mouse cursor, or instead at the 3d cursor",
        default=False,
    )

    link_method: EnumProperty(
        items=[
            ("LINK", "Link", "Link"),
            ("APPEND", "Append", "Append"),
            ("APPEND_REUSE", "Append reuse", "Append reuse"),
        ],
        default="APPEND_REUSE",
    )

    material_slot = None

    def invoke(self, context, event):
        # This is the best way I know to be able to pass custom data to operators
        self.material_slot = self.__class__.material_slot
        self.__class__.material_slot = None

        # Store mouse positions
        self.mouse_pos_region = V((event.mouse_region_x, event.mouse_region_y))
        self.mouse_pos_window = V((event.mouse_x, event.mouse_y))
        return self.execute(context)

    def execute(self, context):

        # Find 3D coordinates of the point under the mouse cursor
        if self.at_mouse:
            try:
                location = point_under_mouse(context, self.mouse_pos_region, self.mouse_pos_window)
            except ValueError:
                message = "Cannot import assets when the preferences window is active. \
                Blender is weird like that :(".replace("  ", "")
                report_message("ERROR", message)
                return {"CANCELLED"}
        else:
            location = V(self.location)

        asset_list_item = get_asset_lists().all_assets.get(self.asset_name)
        asset = asset_list_item.to_asset(self.asset_quality, self.link_method)

        if self.at_mouse and asset_list_item.type in {HDRI, MATERIAL} and len(context.window_manager.windows) > 1:
            report_message(
                "WARNING",
                "Downloading hdris and materials may not work as expected when Blender has multiple windows open. \
                Blender is weird :(".replace("  ", ""),
            )

        # This is needed to prevent errors
        material_slot = self.material_slot
        download_and_import_asset(context, asset, material_slot, draw=True, location=location)
        return {"FINISHED"}