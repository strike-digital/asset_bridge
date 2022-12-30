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
from asset_bridge.settings import AssetBridgeIDSettings

start = perf_counter()

parser = argparse.ArgumentParser()
parser.add_argument("--asset_list_name")
args = sys.argv[sys.argv.index('--') + 1:]
args = parser.parse_args(args)

asset_list = get_asset_lists()[args.asset_list_name]

catalog = AssetCatalogFile(DIRS.asset_browser)
catalog.reset()

type_to_data = {World: bpy.data.worlds, Object: bpy.data.objects, Material: bpy.data.materials}


def get_asset_data(asset) -> AssetBridgeIDSettings:
    return asset.asset_bridge


# Create a data block for each asset, and set it's properties
for asset_item in asset_list.values():
    params = {}
    if asset_item.bl_type == Object:
        params["object_data"] = None
    asset: Object = type_to_data[asset_item.bl_type].new(asset_item.label, **params)

    # Set asset bridge attributes
    data = get_asset_data(asset)
    data.is_asset_bridge = True
    data.idname = asset_item.idname

    # Set blender asset attributes
    asset.asset_mark()
    asset.asset_data.author = asset_item.authors[0]
    asset.asset_data.description = asset_item.idname
    for tag in asset_item.tags:
        asset.asset_data.tags.new(tag)

    # Load previews
    with bpy.context.temp_override(id=asset):
        bpy.ops.ed.lib_id_load_custom_preview(filepath=str(DIRS.previews / f"{asset_item.idname}.png"))

# Save
blend_file = DIRS.dummy_assets / (asset_list.name + ".blend")
bpy.ops.wm.save_mainfile(filepath=str(blend_file), check_existing=False)

# Remove blend1 file
blend1_file = DIRS.dummy_assets / (asset_list.name + ".blend1")
if blend1_file.exists():
    os.remove(blend1_file)

print(f"Finished in {perf_counter() - start:.2f}s")

bpy.ops.wm.quit_blender()