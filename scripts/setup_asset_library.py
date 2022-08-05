import bpy
# from ..constants import BASE_ASSET_NAME

print("Here!")
# bpy.data.objects.clear()
base_asset = bpy.data.objects["__base_asset__"]
print(base_asset)

bpy.ops.wm.save_mainfile()
bpy.ops.wm.quit_blender()