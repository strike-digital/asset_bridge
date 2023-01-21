import argparse
import os
from pathlib import Path
import sys
from time import perf_counter
import bpy
import addon_utils
from bpy.types import Material, Object, World

addon_utils.enable(Path(__file__).parents[1].name)
from asset_bridge.api import get_asset_lists
from asset_bridge.constants import DIRS
from asset_bridge.settings import get_asset_settings
from asset_bridge.catalog import AssetCatalogFile
"""Creates all of the dummy assets for the given asset list that will be shown in the asset browser.
These are empty materials, objects etc. which are swapped out automatically when they are dragged into the scene"""

# TODO: Only set up the assets that need to be, to speed up getting new assets

parser = argparse.ArgumentParser()
parser.add_argument("--asset_list_name")
args = sys.argv[sys.argv.index('--') + 1:]
args = parser.parse_args(args)

asset_list = get_asset_lists()[args.asset_list_name]
progress_file = DIRS.dummy_assets / f"{asset_list.name}_progress.txt"


def update_progress_file(value):
    # Write the new progress value
    with open(progress_file, "w") as f:
        f.write(str(value))


update_progress_file(0)

# setup catalog file
catalog = AssetCatalogFile(DIRS.dummy_assets, f"{asset_list.name}.cats.txt", load_from_file=False)
catalog.add_catalog(asset_list.label)

paths = set()

# Add the catalog paths
for asset_item in asset_list.values():
    name = asset_item.catalog_path.split('/')[-1]
    paths.add(f"{asset_list.label}/{asset_item.catalog_path}")

# Add the intermediate paths (so that the names don't have the asterisk next to them in the asset browser)
intermediate_paths = set()

for path in paths:
    parts = path.split('/')
    # print(parts, name, flush=True)
    catalog.ensure_catalog_exists(parts[-1], path)
    for i, part in enumerate(parts[:-1]):
        intermediate_paths.add("/".join(parts[:i + 1]))

for path in intermediate_paths:
    catalog.ensure_catalog_exists(path.split('/')[-1], path)

catalog.write()

# Convert between bpy.types and bpy.data
type_to_data = {World: bpy.data.worlds, Object: bpy.data.objects, Material: bpy.data.materials}


progress = 0
progress_update_interval = .01
last_update = 0

# Create a data block for each asset, and set it's properties
for i, asset_item in enumerate(asset_list.values()):
    params = {}
    if asset_item.bl_type == Object:
        params["object_data"] = None
    asset: Object = type_to_data[asset_item.bl_type].new(asset_item.label, **params)

    # Set asset bridge attributes
    data = get_asset_settings(asset)
    data.is_dummy = True
    data.idname = asset_item.idname

    # Set blender asset attributes
    asset.asset_mark()
    asset.asset_data.author = asset_item.authors[0]
    asset.asset_data.description = asset_item.idname
    for tag in asset_item.tags:
        asset.asset_data.tags.new(tag)

    tags = set(asset_item.tags)
    if asset_item.type not in tags:
        asset.asset_data.tags.new(asset_item.type)

    # Load previews (This is the slowest part, not sure how to speed it up)
    with bpy.context.temp_override(id=asset):
        bpy.ops.ed.lib_id_load_custom_preview(filepath=str(DIRS.previews / f"{asset_item.idname}.png"))

    # Set the catalog
    asset.asset_data.catalog_id = catalog[asset_list.label + "/" + asset_item.catalog_path].uuid

    # Update the progress
    progress += 1
    if perf_counter() - last_update > progress_update_interval:
        update_progress_file(progress)
        last_update = perf_counter()

# Save
blend_file = DIRS.dummy_assets / (asset_list.name + ".blend")
bpy.ops.wm.save_mainfile(filepath=str(blend_file), check_existing=False)

# Remove blend1 file
blend1_file = DIRS.dummy_assets / (asset_list.name + ".blend1")
if blend1_file.exists():
    os.remove(blend1_file)

bpy.ops.wm.quit_blender()