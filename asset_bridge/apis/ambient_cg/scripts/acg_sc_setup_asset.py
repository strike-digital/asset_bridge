import argparse
import os
import sys
from pathlib import Path

import bpy

asset_utils = Path(__file__).parents[2]
sys.path.append(str(asset_utils))

parser = argparse.ArgumentParser()
parser.add_argument("--name")
parser.add_argument("--output_file")
args = sys.argv[sys.argv.index("--") + 1 :]
args = parser.parse_args(args)

objs = [obj for obj in bpy.data.objects]
for obj in objs:
    bpy.data.objects.remove(obj)

name = args.name
collection = bpy.data.collections.new(name)
bpy.context.scene.collection.children.link(collection)

folder = Path(args.output_file).parent
for file in folder.iterdir():
    if file.suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(file))

for obj in bpy.context.scene.objects:
    obj.select_set(True)
    collection.objects.link(obj)

# for mat in bpy.data.materials:
#     mat: Material
#     if mat.use_nodes:
#         for node in mat.node_tree.nodes:
#             node: bpy.types.Node
#             if node.bl_idname == "ShaderNodeTexImage":
#                 if node.outputs[0] and node.outputs[0].links:
#                     to_node = node.outputs[0].links[0].to_node
#                     if to_node.bl_idname == "ShaderNodeNormalMap"

for image in bpy.data.images:
    name_parts = image.name.split("_")
    if "Color" not in name_parts[-1]:
        image: bpy.types.Image
        image.colorspace_settings.is_data = True

bpy.ops.object.shade_smooth()

# bpy.ops.wm.save_mainfile(filepath=str(Path(bpy.data.filepath).parent / f"{args.name}.blend"))
bpy.ops.wm.save_mainfile(filepath=args.output_file)

# Remove blend1 file
blend1_file = Path(bpy.data.filepath + "1")
if blend1_file.exists():
    os.remove(blend1_file)

bpy.ops.wm.quit_blender()
