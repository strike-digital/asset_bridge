from pathlib import Path
import bpy

name = Path(bpy.data.filepath).parts[-1].replace(".blend", "")
collection = bpy.data.collections.new(name)

for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        collection.objects.link(obj)

bpy.context.scene.collection.children.link(collection)
bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
bpy.ops.wm.quit_blender()