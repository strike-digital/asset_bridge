from time import time
import bpy
from pathlib import Path
import sys

addon_path = Path(__file__).parents[1]
sys.path.append(str(addon_path))
from constants import FILES, DIRS
from assets import AssetList
from catalog import AssetCatalogFile

asset_list = AssetList(FILES.asset_list)
catalog = AssetCatalogFile(DIRS.asset_browser)
catalog.reset()

singular = {"hdris": "hdri", "textures": "texture", "models": "model"}

categories = {}

for asset_type in ("hdris", "textures", "models"):
    catalog.ensure_catalog_exists(asset_type.title())
    for category in getattr(asset_list, singular[asset_type] + "_categories"):
        category = category.capitalize()
        path = f"{asset_type.title()}/{category}"
        categories[path] = False
        catalog.ensure_catalog_exists(category, "/".join([asset_type.title(), category]))

progress = 0
start = time()


def update_progress():
    with open(FILES.script_progress, "w") as f:
        f.write(str(progress))


def add_asset_attrs(asset, name, info, path):
    global progress
    global start
    asset.is_asset_bridge = True
    asset.asset_bridge_name = name
    asset.asset_mark()
    asset.asset_data.author = ", ".join(info["authors"])
    for tag in info["tags"]:
        asset.asset_data.tags.new(tag)
    with bpy.context.temp_override(id=asset):
        bpy.ops.ed.lib_id_load_custom_preview(filepath=str(DIRS.previews / f"{name}.png"))
    cats = info["categories"]
    cat = cats[-1].capitalize()
    path = f"{path}/{cat}"
    asset.asset_data.catalog_id = catalog[path].uuid
    categories[path] = True

    # Update progress file
    progress += 1
    if time() - start > .02:
        update_progress()
        start = time()


bpy.types.Object.is_asset_bridge = bpy.props.BoolProperty()
bpy.types.Object.asset_bridge_name = bpy.props.StringProperty()

# setup assets
for name, asset in asset_list.models.items():
    obj = bpy.data.objects.new(asset["name"], None)
    add_asset_attrs(obj, name, asset, "Models")

bpy.types.Material.is_asset_bridge = bpy.props.BoolProperty()
bpy.types.Material.asset_bridge_name = bpy.props.StringProperty()

for name, asset in asset_list.textures.items():
    mat = bpy.data.materials.new(asset["name"])
    add_asset_attrs(mat, name, asset, "Textures")

bpy.types.World.is_asset_bridge = bpy.props.BoolProperty()
bpy.types.World.asset_bridge_name = bpy.props.StringProperty()

for name, asset in asset_list.hdris.items():
    world = bpy.data.worlds.new(asset["name"])
    add_asset_attrs(world, name, asset, "Hdris")

for cat, val in categories.items():
    if not val:
        catalog.remove_catalog(cat)

bpy.ops.wm.save_mainfile(filepath=str(FILES.asset_lib_blend))
bpy.ops.wm.quit_blender()