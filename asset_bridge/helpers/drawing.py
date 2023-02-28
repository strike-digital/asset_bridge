import bpy
from bpy.types import Region, Context
from mathutils import Vector as V
from bpy_extras.view3d_utils import (region_2d_to_origin_3d, region_2d_to_vector_3d)

from ..operators.op_report_message import report_message


def mouse_in_window_bounds(mouse_pos, window):
    print(window.x, window.y, window.width, window.height, mouse_pos)
    return (window.x < mouse_pos.x < window.x + window.width) and (window.y < mouse_pos.y < window.y + window.height)


def get_active_area(mouse_pos):
    """Get the area the under the mouse position"""
    mouse_pos = V(mouse_pos)

    for area in bpy.context.screen.areas:
        if (area.x < mouse_pos.x < area.x + area.width) and (area.y < mouse_pos.y < area.y + area.height):
            return area
    else:
        return None


def get_active_window_region(mouse_pos, fallback_area_type=""):
    """Get the window region of the area under the mouse position,
    The fallback area with the largest size is used if the region cannot be found"""
    area = get_active_area(mouse_pos)
    if not area and fallback_area_type:
        areas = set()
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == fallback_area_type:
                    areas.add(area)

        if areas:
            area = max(areas, key=lambda area: area.width + area.height)

    if area:
        for region in area.regions:
            if region.type == "WINDOW":
                return region
    return None


def point_under_mouse(context: Context, mouse_pos_region: V, mouse_pos_window: V = None, region: Region = None):
    """Return the point in 3D space under the mouse position

    Args:
        region (Region): The window region of the 3D view area
        mouse_pos_region (V): The region relative position of the mouse

    Returns:
        Vector: The location of the point under the mouse
    """
    if not region:
        if context.region:
            region = context.region
        else:
            region = get_active_window_region(mouse_pos_window, fallback_area_type="VIEW_3D")
            mouse_pos_region = mouse_pos_window - V((region.x, region.y))
            # TODO: Try and fix this
            if not region:
                raise ValueError("Cannot find the active region")
            if any(c < 0 for c in mouse_pos_region):
                mouse_pos_region = V((region.width / 2, region.height / 2))

    depsgraph = context.evaluated_depsgraph_get()
    r3d = region.data

    view_vector = V(region_2d_to_vector_3d(region, r3d, mouse_pos_region))
    ray_origin = V(region_2d_to_origin_3d(region, r3d, mouse_pos_region))

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
    return location