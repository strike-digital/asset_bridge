import bpy
# from ..constants import BASE_ASSET_NAME
from pathlib import Path
import json
import sys

addon_path = Path(__file__).parents[1]
sys.path.append(str(addon_path))
from constants import FILES, PREVIEWS_DIR


list_file = FILES["asset_list"]
with open(list_file, "r") as f:
    asset_list = json.load(f)

bpy.types.Object.is_asset_bridge = bpy.props.BoolProperty()
bpy.types.Object.asset_bridge_name = bpy.props.StringProperty()

# setup assets
for name, asset in asset_list["models"].items():
    obj = bpy.data.objects.new(name.replace("_", " ").title(), None)
    obj.is_asset_bridge = True
    obj.asset_bridge_name = name
    obj.asset_mark()
    obj.asset_data.author = list(asset["authors"])[0]
    for tag in asset["tags"]:
        obj.asset_data.tags.new(tag)
    with bpy.context.temp_override(id=obj):
        bpy.ops.ed.lib_id_load_custom_preview(filepath=str(PREVIEWS_DIR / f"{name}.png"))


bpy.ops.wm.save_mainfile(filepath=str(FILES["asset_lib_blend"]))
bpy.ops.wm.quit_blender()