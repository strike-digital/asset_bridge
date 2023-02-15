import bpy
from ..helpers.assets import download_asset, import_asset
from .op_report_message import report_message
from ..helpers.btypes import BOperator
from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..helpers.drawing import get_active_window_region, point_under_mouse
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty, StringProperty
from bpy.types import Operator
from mathutils import Vector as V


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
            # Get the position of the mouse in 3D space
            if context.region:
                region = context.region
                coord = self.mouse_pos_region
            else:
                region = get_active_window_region(self.mouse_pos_window, fallback_area_type="VIEW_3D")
                coord = self.mouse_pos_window - V((region.x, region.y))
                # TODO: Try and fix this
                if not region or any(c < 0 for c in coord):
                    message = "Cannot import assets when the preferences window is active. \
                        Blender is weird like that :(".replace("  ", "")
                    report_message(message, "ERROR")
                    return {"CANCELLED"}

            location = point_under_mouse(context, region, coord)
        else:
            location = V(self.location)

        ab = get_ab_settings(context)
        all_assets = get_asset_lists().all_assets
        asset_list_item = all_assets.get(self.asset_name)
        # These need to variables rather than instance attributes so that they
        # can be accesed in another thread after the operator has finished.
        material_slot = self.material_slot
        asset = asset_list_item.to_asset(self.asset_quality, self.link_method)

        task_name = download_asset(context, asset, draw=True, draw_location=location)

        def check_download():
            if ab.tasks[task_name].cancelled:
                return
            elif ab.tasks[task_name].finished:
                import_asset(context, asset, location, material_slot)
                return
            return .1

        bpy.app.timers.register(check_download, first_interval=.1)
        return {"FINISHED"}