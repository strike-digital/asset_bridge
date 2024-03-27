import argparse
import json
import os
import sys
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Dict

import addon_utils
import bpy
from bpy.types import Material, Object, World

addon_utils.enable(Path(__file__).parents[1].name)

if TYPE_CHECKING:
    from ..api import get_asset_lists
    from ..apis.asset_utils import HDRI, MATERIAL, MODEL
    from ..constants import DIRS, FILES
    from ..helpers.catalog import AssetCatalogFile
    from ..settings import get_asset_settings
else:
    from asset_bridge.api import get_asset_lists
    from asset_bridge.apis.asset_utils import HDRI, MATERIAL, MODEL
    from asset_bridge.constants import DIRS, FILES
    from asset_bridge.helpers.catalog import AssetCatalogFile
    from asset_bridge.settings import get_asset_settings
"""Creates all of the dummy assets for the given asset list that will be shown in the asset browser.
These are empty materials, objects etc. which are swapped out automatically when they are dragged into the scene"""

# TODO: Only set up the assets that need to be, to speed up getting new assets

parser = argparse.ArgumentParser()
parser.add_argument("--asset_list_name")
args = sys.argv[sys.argv.index("--") + 1 :]
args = parser.parse_args(args)

asset_list = get_asset_lists()[args.asset_list_name]
with open(FILES.prefs, "r") as f:
    lib_path = json.load(f)["lib_path"]
DIRS.update(lib_path)
progress_file = DIRS.dummy_assets / f"{asset_list.name}_progress.txt"


def update_progress_file(value):
    # Write the new progress value
    with open(progress_file, "w") as f:
        f.write(str(value))


update_progress_file(0)

# setup catalog file
catalog = AssetCatalogFile(DIRS.dummy_assets, f"{asset_list.name}.cats.txt", load_from_file=False)
# catalog.add_catalog(asset_list.label)

paths = set()

# A dict the popularities of each asset category, separated by type
all_categories: Dict[str, Dict[str, int]] = {}

# Find the popularity of each asset category, separated by type
for asset_item in asset_list.values():
    for category in asset_item.ab_categories:
        # Increment category popularity by 1
        categories = all_categories.get(asset_item.ab_type, {})
        count = categories.get(category, 0)
        categories[category] = count + 1
        all_categories[asset_item.ab_type] = categories

MAX_CATALOG_DEPTH = 3  # The maximum number of child catalogs that can occur under the main type catalogs
ui_names = {HDRI: "HDRIs", MATERIAL: "Materials", MODEL: "Models"}

# Find the catalog path for each asset.
# This works by ordering the assets' categories by popularity, and using that to constuct the path.
# That way, general categories appear at the top of the tree, with many assets in them, and below that
# You can narrow your search by selecting more catalogs.
for asset_item in asset_list.values():
    # Sort the categories by popularity
    categories = all_categories[asset_item.ab_type]
    cats = sorted(asset_item.ab_categories, key=lambda k: categories[k], reverse=True)[:MAX_CATALOG_DEPTH]

    # Remove chains of catalogs that only have one asset in them
    for i in range(len(cats) - 1):
        if categories[cats[i]] <= 1:
            cats = cats[: i + 1]
            break

    # Set the catlog path path
    # path = f"{asset_list.label}/{ui_names[asset_item.ab_type]}/{'/'.join(cats)}"
    path = f"{ui_names[asset_item.ab_type]}/{'/'.join(cats)}"
    asset_item._catalog_path = path
    paths.add(path)

# Add the intermediate paths (so that the names don't have the asterisk next to them in the asset browser)
intermediate_paths = set()

for path in paths:
    parts = path.split("/")
    catalog.ensure_catalog_exists(parts[-1], path)
    for i, part in enumerate(parts[:-1]):
        intermediate_paths.add("/".join(parts[: i + 1]))

for path in intermediate_paths:
    catalog.ensure_catalog_exists(path.split("/")[-1], path)

catalog.write()

# Convert between bpy.types and bpy.data
types_to_data: dict = {World: bpy.data.worlds, Object: bpy.data.objects, Material: bpy.data.materials}

progress = 0
progress_update_interval = 0.01
last_update = 0

# Initial: 1.4s, 2.39s

start = perf_counter()

# Create a data block for each asset, and set it's properties
for i, asset_item in enumerate(asset_list.values()):
    params = {}
    if asset_item.ab_bl_type == Object:
        params["object_data"] = None
    asset = types_to_data[asset_item.ab_bl_type].new(asset_item.ab_label, **params)

    # Set asset bridge attributes
    data = get_asset_settings(asset)
    data.is_dummy = True
    data.idname = asset_item.ab_idname

    # Set blender asset attributes
    asset.asset_mark()
    asset.asset_data.author = asset_item.ab_authors[0]
    asset.asset_data.description = asset_item.ab_idname
    for tag in asset_item.ab_tags:
        asset.asset_data.tags.new(tag)

    tags = set(asset_item.ab_tags)
    if asset_item.ab_type not in tags:
        asset.asset_data.tags.new(asset_item.ab_type)
    asset.asset_data.tags.new(data.idname)
    asset.asset_data.tags.new(asset_list.label)

    # Load previews (This is the slowest part, not sure how to speed it up)
    with bpy.context.temp_override(id=asset):
        bpy.ops.ed.lib_id_load_custom_preview(filepath=str(DIRS.previews / f"{asset_item.ab_idname}.png"))

    # Set the catalog
    # asset.asset_data.catalog_id = catalog[asset_list.label + "/" + asset_item.catalog_path].uuid
    asset.asset_data.catalog_id = catalog[asset_item._catalog_path].uuid

    # Update the progress
    progress += 1
    if perf_counter() - last_update > progress_update_interval:
        update_progress_file(progress)
        last_update = perf_counter()

print(f"created assets in {perf_counter() - start:.3f}s")

# Save
blend_file = DIRS.dummy_assets / (asset_list.name + ".blend")
bpy.ops.wm.save_mainfile(filepath=str(blend_file), check_existing=False)

# Remove blend1 file
blend1_file = DIRS.dummy_assets / (asset_list.name + ".blend1")
if blend1_file.exists():
    os.remove(blend1_file)

bpy.ops.wm.quit_blender()
