import bpy
from mathutils import Vector as V


def get_active_area(mouse_pos):
    """Get the area the under the mouse position"""
    mouse_pos = V(mouse_pos)
    for area in bpy.context.screen.areas:
        if (area.x < mouse_pos.x < area.x + area.width) and (area.y < mouse_pos.y < area.y + area.height):
            return area
    else:
        return None


def get_active_window_region(mouse_pos):
    """Get the window region of the area under the mouse position"""
    area = get_active_area(mouse_pos)
    if area:
        for region in area.regions:
            if region.type == "WINDOW":
                return region
    return None