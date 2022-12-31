import bpy
from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..helpers.drawing import get_active_window_region
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty, StringProperty
from bpy.types import Collection, Object, Operator
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector as V
from ..btypes import BOperator


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

    # link: BoolProperty(
    #     description="Whether to link the asset from the downloaded file, or to append it fully into the scene",
    #     default=False,
    # )

    def invoke(self, context, event):
        self.mouse_pos_region = V((event.mouse_region_x, event.mouse_region_y))
        self.mouse_pos_window = V((event.mouse_x, event.mouse_y))
        return self.execute(context)

    def execute(self, context):

        # Get the position of the mouse in 3D space using raycasting
        if self.at_mouse:
            depsgraph = context.evaluated_depsgraph_get()
            if context.region:
                region = context.region
                coord = self.mouse_pos_region
            else:
                region = get_active_window_region(self.mouse_pos_window)
                coord = self.mouse_pos_window - V((region.x, region.y))
            r3d = region.data

            view_vector = V(region_2d_to_vector_3d(region, r3d, coord))
            ray_origin = V(region_2d_to_origin_3d(region, r3d, coord))

            location = context.scene.ray_cast(depsgraph, ray_origin, view_vector)[1]

            if location == V((0., 0., 0.)):
                # If the ray doesn't intersect with any mesh, place it on the xy plane
                # If view vector intersects with ground behind the camera, just place it in front of the camera
                if (view_vector.z > 0 and ray_origin.z > 0) or (view_vector.z < 0 and ray_origin.z < 0):
                    location = ray_origin + view_vector * (ray_origin.length / 2)
                else:
                    # find the intersection with the ground plane
                    p1 = ray_origin
                    p2 = p1 + view_vector

                    x_slope = (p2.x - p1.x) / (p2.z - p1.z)
                    y_slope = (p2.y - p1.y) / (p2.z - p1.z)
                    xco = p1.x - (x_slope * p1.z)
                    yco = p1.y - (y_slope * p1.z)

                    location = V((xco, yco, 0.))
        else:
            location = V(self.location)

        ab = get_ab_settings(context)
        asset_list_item = get_asset_lists().all_assets[self.asset_name]
        asset = asset_list_item.to_asset(self.asset_quality, self.link_method)

        if not asset_list_item.is_downloaded(self.asset_quality) or ab.reload_asset:
            asset.download_asset()

        def import_asset():
            imported = asset.import_asset(context)

            if isinstance(imported, Object):
                imported.location += location
            elif isinstance(imported, Collection):
                for obj in imported.objects:
                    obj.location += location

        # Blender is weird, and without executing this in a timer, all imported objects will be
        # scaled to zero after execution. God knows why.
        bpy.app.timers.register(import_asset)
        return {"FINISHED"}