import json
import math
from typing import Type

import bpy
from ..constants import DIRS
from ..api import asset_lists
from .asset_types import AssetList
from ..vendor import requests
import shutil
from pathlib import Path


def register_asset_list(new_list: Type[AssetList]):
    """Takes an asset api and initialises all of the asset lists with either cached or new data."""
    # asset_lists[asset_list.name] = asset_list

    # Get the cached asset list data if it exists
    list_file = DIRS.asset_lists / (new_list.name + ".json")
    asset_list_data = {}
    if list_file.exists():
        with open(list_file, "r") as f:
            try:
                asset_list_data = json.load(f)
            except json.JSONDecodeError:
                pass

    # Initialize the asset lists with either the cached data, or new data from the internet, from the get_data function
    if not asset_list_data:
        asset_list_data = new_list.get_data()

    # Ensure that there are no duplicate names in other apis, so that all assets can be accessed by name
    for name, other_list in asset_lists.items():
        if name == new_list.name:
            continue

        if duplicates := other_list.assets.keys() & new_list.assets.keys():
            for duplicate in duplicates:
                asset = new_list[duplicate]
                del new_list[duplicate]
                new_list[f"{duplicate}_1"] = asset
                asset.idname = f"{duplicate}_1"

    # Initialize
    asset_lists[new_list.name] = new_list(asset_list_data)

    # Write the new cached data
    with open(list_file, "w") as f:
        json.dump(asset_list_data, f, indent=2)


def file_name_from_url(url: str) -> str:
    return url.split('/')[-1].split("?")[0]


def download_file(url: str, download_path: Path, file_name: str = ""):
    """Download a file from the provided url to the given file path"""
    if not isinstance(download_path, Path):
        download_path = Path(download_path)

    download_path.mkdir(exist_ok=True)
    file_name = file_name or file_name_from_url(url)
    download_path = download_path / file_name

    result = requests.get(url, stream=True)
    if result.status_code != 200:
        with open(DIRS.addon / "log.txt", "w") as f:
            f.write(url)
            f.write(result.status_code)
        raise requests.ConnectionError()

    with open(download_path, 'wb') as f:
        shutil.copyfileobj(result.raw, f)
    return download_path


def import_hdri(image_file, name, link_method="APPEND_REUSE"):
    """Import an hdri image file as a world and return it"""
    image = bpy.data.images.load(str(image_file), check_existing=link_method in {"LINK", "APPEND_REUSE"})

    world = bpy.data.worlds.new(name)
    world.use_nodes = True
    nodes = world.node_tree.nodes

    background_node = nodes["Background"]
    output_node = nodes["World Output"]
    env_node = nodes.new("ShaderNodeTexEnvironment")
    env_node.image = image

    links = world.node_tree.links
    links.new(env_node.outputs[0], background_node.inputs[0])
    links.new(background_node.outputs[0], output_node.inputs[0])
    return world


def import_model(context, blend_file, name, link_method="APPEND_REUSE"):
    """Import a collection from the given blend file with the given name"""
    link = link_method == "LINK"

    collection = None
    if link:
        # Don't reimport assets that are already linked
        for lib in bpy.data.libraries:
            if Path(lib.filepath) == blend_file:
                try:
                    collection = [coll for coll in lib.users_id if isinstance(coll, bpy.types.Collection)][0]
                except IndexError:
                    pass

    if not collection:
        with bpy.data.libraries.load(filepath=str(blend_file), link=link) as (data_from, data_to):
            # import objects with the correct name, or if none are found, just import all objects
            for coll in data_from.collections:
                if coll == f"{name}":
                    data_to.collections.append(coll)
                    break

    for obj in bpy.data.objects:
        obj.select_set(False)

    collection: bpy.types.Collection = collection or data_to.collections[0]
    if link:
        empty = bpy.data.objects.new(collection.name, None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = collection
        context.collection.objects.link(empty)
        empty.empty_display_size = math.hypot(*list(collection.objects[0].dimensions))
        empty.select_set(True)
        final_obj = empty
        retval = empty
    else:
        context.collection.children.link(collection)

        # Set the selection
        final_obj = None
        for obj in collection.objects:
            obj.select_set(True)
            obj.name = f"{name}"
            final_obj = obj
        retval = collection

    context.view_layer.objects.active = final_obj
    # Blender is weird, and without pushing an undo step
    # linking the object to the active collection will cause a crash.
    bpy.ops.ed.undo_push()
    return retval