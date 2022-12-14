import argparse
import os
from pathlib import Path
import sys
import bpy

parser = argparse.ArgumentParser()
parser.add_argument("--name")
args = sys.argv[sys.argv.index("--") + 1:]
args = parser.parse_args(args)

# name = Path(bpy.data.filepath).parts[-1].replace(".blend", "")
name = args.name
collection = bpy.data.collections.new(name)

for obj in bpy.context.scene.objects:
    collection.objects.link(obj)

bpy.context.scene.collection.children.link(collection)
bpy.ops.wm.save_mainfile(filepath=str(Path(bpy.data.filepath).parent / f"{args.name}.blend"))

# Remove blend1 file
blend1_file = Path(bpy.data.filepath + "1")
if blend1_file.exists():
    os.remove(blend1_file)

bpy.ops.wm.quit_blender()