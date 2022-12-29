from pathlib import Path
import bpy
import addon_utils

addon_utils.enable(Path(__file__).parents[1].name)
from asset_bridge.api import get_asset_lists

print(get_asset_lists())

print("ho!")
bpy.ops.wm.quit_blender()