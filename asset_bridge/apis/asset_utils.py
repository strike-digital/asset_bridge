import json
import math
from typing import Type

from mathutils import Vector as V
from ..ui import dpifac

import bpy
from ..constants import DIRS
from ..api import asset_lists
from .asset_types import AssetList
from ..vendor import requests
import shutil
from pathlib import Path


HDRI = "hdri"
MATERIAL = "material"
MODEL = "model"


"""Contains useful common functions to be used by the various apis"""


def register_asset_list(new_list: Type[AssetList]):
    """"""
    asset_lists[new_list.name] = new_list
    # Get the cached asset list data if it exists
    list_file = DIRS.asset_lists / (new_list.name + ".json")
    asset_list_data = {}
    if list_file.exists():
        with open(list_file, "r") as f:
            try:
                asset_list_data = json.load(f)
            except json.JSONDecodeError:
                pass

    if not asset_list_data:
        # no cached data found, wait for user to initialize the asset list.
        return

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


def file_name_from_url(url: str) -> str:
    """Extract the file name from a URL"""
    return url.split('/')[-1].split("?")[0]


def download_file(url: str, download_dir: Path, file_name: str = ""):
    """Download a file from the provided url to the given file path"""
    if not isinstance(download_dir, Path):
        download_dir = Path(download_dir)

    download_dir.mkdir(exist_ok=True)
    file_name = file_name or file_name_from_url(url)
    download_dir = download_dir / file_name

    result = requests.get(url, stream=True)
    if result.status_code != 200:
        with open(DIRS.addon / "log.txt", "w") as f:
            f.write(url)
            f.write(result.status_code)
        raise requests.ConnectionError()

    with open(download_dir, 'wb') as f:
        shutil.copyfileobj(result.raw, f)
    return download_dir


def load_image(image_file, link_method, name=""):
    """Load an image file according to the given link_method."""
    image = bpy.data.images.load(str(image_file), check_existing=link_method in {"LINK", "APPEND_REUSE"})
    if name:
        image.name = name
    return image


def dimensions_to_string(dimensions: list[float] | str) -> str:
    """Show dimensions in metric or imperial units depending on scene settings.
    This is my gift to the americans, burmese and the liberians of the world.
    The dimensions can be either a list or the string representation of a list (used for asset metadata)."""
    unit_system = bpy.context.scene.unit_settings.system
    if unit_system in ["METRIC", "NONE"]:
        coefficient = 1
        suffix = "m"
    else:
        coefficient = 3.2808399
        suffix = "ft"
    if isinstance(dimensions, str):
        dims = json.loads(dimensions)
    else:
        dims = dimensions
    string = ""
    for dim in dims:
        string += f"{dim / 1000 * coefficient:.0f}{suffix} x "
    string = string[:-3]
    return string


def import_hdri(image_file, name, link_method="APPEND_REUSE"):
    """Import an hdri image file as a world and return it"""
    image = load_image(image_file, link_method)

    # Set up world
    world = bpy.data.worlds.new(name)
    world.use_nodes = True
    nodes = world.node_tree.nodes

    # Add nodes
    background_node = nodes["Background"]
    output_node = nodes["World Output"]
    env_node = nodes.new("ShaderNodeTexEnvironment")
    env_node.image = image

    # Link nodes
    links = world.node_tree.links
    links.new(env_node.outputs[0], background_node.inputs[0])
    links.new(background_node.outputs[0], output_node.inputs[0])
    return world


def import_material(texture_files: dict, name: str, link_method="APPEND_REUSE"):
    """import the provided PBR texture files as a material and return it"""
    if not texture_files:
        raise ValueError("Cannot import material when not texture files are provided")

    # Use existing material if it is the correct link method
    mat = bpy.data.materials.get(name)
    if mat and link_method != "APPEND":
        return mat

    # Create material
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf_node = nodes["Principled BSDF"]
    out_node = nodes["Material Output"]
    image_nodes = []
    disp_node = None
    nor_node = None

    def new_image(file, input_index, node_name="", to_node=None, non_color=False):
        """Add a new image node, and connect it to the given to_node if provided, or the bsdf node"""
        if not to_node:
            to_node = bsdf_node
        image_node = nodes.new("ShaderNodeTexImage")
        image_node.name = image_node.label = node_name
        image = load_image(file, link_method)
        image_node.image = image
        links.new(image_node.outputs[0], to_node.inputs[input_index])
        image_nodes.append(image_node)
        if non_color:
            image.colorspace_settings.name = "Non-Color"
        return image

    # Add images
    if diff_file := texture_files.get("diffuse"):
        new_image(diff_file, "Base Color", "Diffuse")

    if rough_file := texture_files.get("roughness"):
        new_image(rough_file, "Roughness", "Roughness", non_color=True)

    if nor_file := texture_files.get("normal"):
        nor_node = nodes.new("ShaderNodeNormalMap")
        new_image(nor_file, "Color", "Normal", to_node=nor_node, non_color=True)
        links.new(nor_node.outputs[0], bsdf_node.inputs["Normal"])

    if disp_file := texture_files.get("displacement"):
        disp_node = nodes.new("ShaderNodeDisplacement")
        new_image(disp_file, "Height", "Displacement", to_node=disp_node)
        links.new(disp_node.outputs[0], out_node.inputs["Displacement"])

    # Add mapping and set locations
    mapping_node = nodes.new("ShaderNodeMapping")
    mapping_node.name = mapping_node.label = "Mapping"
    half_height = (300 * (len(image_nodes) - 1) / 2)
    for i, node in enumerate(image_nodes):
        x = bsdf_node.location.x - (node.width + 200) * dpifac()
        y = bsdf_node.location.y - 300 * i + half_height - 200
        node.location = (x, y)
        links.new(mapping_node.outputs[0], node.inputs[0])
    mapping_node.location = (node.location.x - mapping_node.width - 80, bsdf_node.location.y)

    # Add texture coordinates
    coords_node = nodes.new("ShaderNodeTexCoord")
    coords_node.name = coords_node.label = "Coords"
    links.new(coords_node.outputs["UV"], mapping_node.inputs[0])
    coords_node.location = mapping_node.location - V((coords_node.width + 40, 0))

    # Add normal and displacement nodes
    if nor_node:
        nor_image_node = nodes["Normal"]
        nor_node.location = nor_image_node.location + V((nor_image_node.width + 40, 0))

    if disp_node:
        # TODO: Get the average color and use it as the material color
        # TODO: Add a preference for the default displacement method
        # Maybe calculate the average displace value and use it as the midlevel
        mat.cycles.displacement_method = "DISPLACEMENT"
        disp_node.location = bsdf_node.location + V((bsdf_node.width - disp_node.width, -680))
    return mat


def import_model(context, blend_file, name, link_method="APPEND_REUSE"):
    """Import a collection from the given blend file with the given name"""
    # TODO: imlement the append_reuse link method for objects
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

    # Import the collection with the correct name from the blend file. Raises an error if it can't be found
    if not collection:
        with bpy.data.libraries.load(filepath=str(blend_file), link=link) as (data_from, data_to):
            for coll in data_from.collections:
                if coll == f"{name}":
                    data_to.collections.append(coll)
                    break
            else:
                raise KeyError(f"Key {name} not found in collections {data_from.collections}\nIn blend file: {blend_file}")

    for obj in bpy.data.objects:
        obj.select_set(False)

    collection: bpy.types.Collection = collection or data_to.collections[0]
    if link:
        # Create an empty to use as an instance collection so that it can be moved by the user.
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