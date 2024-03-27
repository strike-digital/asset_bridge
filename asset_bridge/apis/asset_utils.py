import json
import math
from pathlib import Path
from shutil import copyfileobj
from time import perf_counter
from typing import Dict, Literal, Type

import bpy
from bpy.types import Material, Node, NodeGroup, Object
from mathutils import Vector as V

from ..api import asset_lists
from ..constants import __IS_DEV__, FILES, NODE_GROUPS, NODES, ServerError503
from ..helpers.prefs import get_prefs
from ..previews import load_icon
from ..settings import get_ab_scene_settings
from ..ui.ui_helpers import dpifac
from ..vendor import requests
from .asset_types import AssetList

HDRI = "hdri"
MATERIAL = "material"
MODEL = "model"
"""Contains useful common functions to be used by the various asset lists"""


def register_asset_list(new_list: Type[AssetList]):
    """Register an asset list to be used by the addon"""

    def reg_in_thread():
        start = perf_counter()
        asset_lists[new_list.name] = new_list
        # Get the cached asset list data if it exists
        list_file = new_list.data_cache_file
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

        asset_list = asset_lists.initialize_asset_list(new_list.name, data=asset_list_data)
        if asset_list is None:
            return {"CANCELLED"}

        # Load the list icon if it exists
        load_icon(asset_list.icon_path)

        if __IS_DEV__:
            print(f"Initialization for {new_list.name} took {perf_counter() - start:.2f}s")

    # Load the asset list in another thread to prevent locking the UI and slowing down blender loading.
    # Turns out this can cause crashes. Would be good to fix in the future.
    # thread = Thread(target=reg_in_thread)
    # thread.start()

    reg_in_thread()
    return


def file_name_from_url(url: str) -> str:
    """Extract the file name from a URL"""
    return url.split("/")[-1].split("?")[0]


def download_file(url: str, download_dir: Path, file_name: str = "", use_progress_file=True):
    """Download a file from the provided url to the given file path"""
    if not isinstance(download_dir, Path):
        download_dir = Path(download_dir)

    download_dir.mkdir(exist_ok=True, parents=True)
    file_name = file_name or file_name_from_url(url)
    download_file = download_dir / file_name
    # progress_file = download_dir / f"{file_name}.progress.txt"

    with requests.get(url, stream=True) as result:
        if result.status_code != 200:
            with open(FILES.download_log, "w") as f:
                f.write(url)
                f.write("\n")
                f.write(str(result.status_code))

            # This can be handled specially to provide better information to the user.
            if result.status_code == 503:
                raise ServerError503(url)

            raise requests.ConnectionError(
                f"Could not download file at url:\n{url}\nbecause of a connection error (code {result.status_code})"
            )
        with open(download_file, "wb") as f:
            copyfileobj(result.raw, f)
            # for chunk in result.iter_content(chunk_size=8192):
            #     size = f.write(chunk)
            #     total += size
            #     if progress_file and time() - last_write > .05:
            #         with open(progress_file, "w") as pf:
            #             pf.write(str(total))
            #         last_write = time()

    # if progress_file.exists():
    #     os.remove(progress_file)

    return download_file


def load_image(image_file, link_method, name=""):
    """Load an image file according to the given link_method."""
    image = bpy.data.images.load(str(image_file), check_existing=link_method in {"LINK", "APPEND_REUSE"})
    if get_prefs(bpy.context).auto_pack_files:
        image.pack()
    if name:
        image.name = name
    return image


def dimensions_to_string(dimensions: list[float] | str) -> str:
    """Show dimensions in metric or imperial units depending on scene settings.
    This is my gift to the americans, burmese and the liberians of the world.
    The dimensions can be either a list or the string representation of a list (used for asset metadata)."""
    if isinstance(dimensions, str):
        dims = json.loads(dimensions)
    else:
        dims = dimensions

    unit_system = bpy.context.scene.unit_settings.system
    if unit_system in ["METRIC", "NONE"]:
        if dims[0] / 1000 > 0.999999:
            coefficient = 1
            suffix = "m"
        else:
            coefficient = 1000
            suffix = "cm"
    else:
        coefficient = 3.2808399
        if dims[0] / 1000 * coefficient > 1:
            suffix = "ft"
        else:
            coefficient = coefficient * 12
            suffix = "in"

    string = ""
    for dim in dims:
        size = dim / 1000 * coefficient
        decimal = 0 if size > 0.99999 else 1
        string += f"{size:.{decimal}f}{suffix} x "
    string = string[:-3]
    return string


def get_node_group(blend_file: Path, node_group_name: str, link_method: str = "APPEND_REUSE") -> NodeGroup:
    """Append a node group to the current blend file.

    Args:
        blend_file (Path): The path to the blend file containing the node group.
        node_group_name (str): The name of the node group to append.
        link_method (str, optional): One of ["LINK", "APPEND", "APPEND_REUSE"]. Defaults to "APPEND_REUSE".

    Returns:
        NodeGroup: the appended node group.
    """

    if link_method == "APPEND_REUSE" and node_group_name in set(bpy.data.node_groups.keys()):
        return bpy.data.node_groups[node_group_name]

    with bpy.data.libraries.load(str(blend_file), link=link_method == "LINK") as (data_from, data_to):
        if node_group_name not in data_from.node_groups:
            raise KeyError(f"Name {node_group_name} could not be appended, not found in {list(data_from.node_groups)}")

        data_to.node_groups.append(node_group_name)

    return data_to.node_groups[0]


def import_hdri(image_file, name, link_method="APPEND_REUSE"):
    """Import an hdri image file as a world and return it"""
    image = load_image(image_file, link_method)

    # Set up world
    world = bpy.data.worlds.new(name)
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Add nodes
    background_node = nodes["Background"]
    nodes.remove(background_node)
    output_node = nodes["World Output"]

    coords_node = nodes.new("ShaderNodeGroup")
    coords_node_group = get_node_group(FILES.resources_blend, NODE_GROUPS.hdri_coords)
    coords_node.node_tree = coords_node_group
    coords_node.name = NODE_GROUPS.hdri_coords

    env_node = nodes.new("ShaderNodeTexEnvironment")
    env_node.image = image
    links.new(coords_node.outputs[0], env_node.inputs[0])

    color_node = nodes.new("ShaderNodeGroup")
    color_node_group = get_node_group(FILES.resources_blend, NODE_GROUPS.hdri_color)
    color_node.node_tree = color_node_group
    color_node.name = NODE_GROUPS.hdri_color
    links.new(env_node.outputs[0], color_node.inputs[0])
    links.new(color_node.outputs[0], output_node.inputs[0])

    # Recursively set the position of all nodes in the tree
    def set_node_pos(node: Node, prev_pos: V):
        node.location = prev_pos - V((node.width + 20, 0))
        if node.inputs[0].links:
            next_node = node.inputs[0].links[0].from_node
            set_node_pos(next_node, node.location)

    set_node_pos(output_node, V((0, 0)))

    return world


def import_material(
    texture_files: Dict[Literal["diffuse", "ao", "roughness", "metalness", "normal", "displacement", "opacity"], Path],
    name: str,
    link_method="APPEND_REUSE",
    mute_displacement=True,
) -> Material:
    """import the provided PBR texture files as a material and return it

    Args:
        texture_files (Dict[str, Path]): A dictionary of file paths to the supported texture files (see type hint).
        name (str): The name of the imported material
        link_method (str, optional): The link method to use. Defaults to "APPEND_REUSE".
        real_world_size (float, optional): The real world size of the textures, used to apply the correct scaling

    Returns:
        bpy.types.Material: The imported material
    """
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
    bsdf_node.name = NODES.principled_bsdf
    out_node = nodes["Material Output"]
    image_nodes = []
    disp_node = diff_node = nor_node = rough_group_node = ao_mix_node = hsv_node = None

    def new_image(file, input_index, node_name="", to_node=None, non_color=True):
        """Add a new image node, and connect it to the given to_node if provided, or the bsdf node"""
        if not to_node:
            to_node = bsdf_node
        image_node = nodes.new("ShaderNodeTexImage")
        image_node.name = image_node.label = node_name
        image = load_image(file, link_method)
        image_node.image = image
        links.new(image_node.outputs[0], to_node.inputs[input_index])
        image_nodes.append(image_node)
        image.colorspace_settings.is_data = non_color
        return image_node

    # Add images
    if diff_file := texture_files.get("diffuse"):
        diff_node = new_image(diff_file, "Base Color", "Diffuse", non_color=False)

        # Ambient occlusion
        if ao_file := texture_files.get("ao"):
            ao_mix_node = nodes.new("ShaderNodeMix")
            ao_mix_node.label = "AO Mix"
            ao_mix_node.name = NODES.ao_mix
            ao_mix_node.data_type = "RGBA"
            ao_mix_node.blend_type = "MULTIPLY"
            links.new(diff_node.outputs[0], ao_mix_node.inputs[6])
            links.new(ao_mix_node.outputs[2], bsdf_node.inputs["Base Color"])
            ao_image_node = new_image(ao_file, 7, "Ambient Occlusion", to_node=ao_mix_node)

        hsv_node = nodes.new("ShaderNodeHueSaturation")
        hsv_node.name = NODES.hsv
        links.new(diff_node.outputs[0], hsv_node.inputs["Color"])
        links.new(hsv_node.outputs["Color"], ao_mix_node.inputs[6] if ao_mix_node else bsdf_node.inputs["Base Color"])

    if metal_file := texture_files.get("metalness"):
        new_image(metal_file, "Metallic", "Metalness")

    if rough_file := texture_files.get("roughness"):
        rough_node = new_image(rough_file, "Roughness", "Roughness")

        rough_group_node = nodes.new("ShaderNodeGroup")
        rough_group_node.node_tree = get_node_group(
            FILES.resources_blend,
            NODE_GROUPS.roughness_map,
            link_method=link_method,
        )
        rough_group_node.name = NODES.roughness
        links.new(rough_node.outputs[0], rough_group_node.inputs[0])
        links.new(rough_group_node.outputs[0], bsdf_node.inputs["Roughness"])

    if emission_file := texture_files.get("emission"):
        new_image(emission_file, "Emission", "Emission", non_color=False)

    if opacity_file := texture_files.get("opacity"):
        opacity_node = new_image(opacity_file, "Alpha", "Opacity")
        opacity_node.name = NODES.opacity
        mat.blend_method = "CLIP"
        mat.shadow_method = "CLIP"

    if nor_file := texture_files.get("normal"):
        nor_node = nodes.new("ShaderNodeGroup")
        nor_node.node_tree = get_node_group(FILES.resources_blend, NODE_GROUPS.normal_map, link_method)
        # nor_node = nodes.new("ShaderNodeNormalMap")
        nor_node.name = NODES.normal_map
        new_image(nor_file, "Color", "Normal", to_node=nor_node)
        links.new(nor_node.outputs[0], bsdf_node.inputs["Normal"])

    if disp_file := texture_files.get("displacement"):
        disp_node = nodes.new("ShaderNodeDisplacement")
        disp_node.name = NODES.displacement
        new_image(disp_file, "Height", "Displacement", to_node=disp_node)
        link = links.new(disp_node.outputs[0], out_node.inputs["Displacement"])
        link.is_muted = mute_displacement

    # Add mapping and set locations
    mapping_node = nodes.new("ShaderNodeMapping")
    mapping_node.name = NODES.mapping
    mapping_node.label = "Mapping"
    half_height = 300 * (len(image_nodes) - 1) / 2
    for i, node in enumerate(image_nodes):
        x = bsdf_node.location.x - (node.width + 180) * dpifac()
        y = bsdf_node.location.y - 300 * i + half_height - 200
        node.location = (x, y)
        links.new(mapping_node.outputs[0], node.inputs[0])
    mapping_node.location = (node.location.x - mapping_node.width - 80, bsdf_node.location.y)

    # Add scale node
    scale_node = nodes.new("ShaderNodeVectorMath")
    scale_node.operation = "SCALE"
    links.new(scale_node.outputs[0], mapping_node.inputs[0])
    scale_node.location = mapping_node.location - V((scale_node.width + 40, 0))

    # Set up anti tiling node group
    node_group = get_node_group(FILES.resources_blend, NODE_GROUPS.anti_tiling, link_method=link_method)
    anti_tiling_node = nodes.new("ShaderNodeGroup")
    anti_tiling_node.node_tree = node_group
    anti_tiling_node.location = scale_node.location - V((anti_tiling_node.width + 40, 0))
    anti_tiling_node.name = NODE_GROUPS.anti_tiling
    anti_tiling_node.label = "Anti tiling"
    anti_tiling_node.mute = True
    links.new(anti_tiling_node.outputs[0], scale_node.inputs[0])

    # Add displacement scaling nodes
    if disp_node:
        value_node = nodes.new("ShaderNodeValue")
        value_node.outputs[0].default_value = 1
        value_node.name = NODES.scale
        value_node.label = "Scale"
        value_node.location = anti_tiling_node.location + (V((0, -350)))

        links.new(value_node.outputs[0], scale_node.inputs[3])

        math_node = nodes.new("ShaderNodeMath")
        math_node.name = NODES.displacement_strength
        math_node.label = "Displacement Strength"
        math_node.inputs[0].default_value = 1
        math_node.operation = "DIVIDE"
        image_node = image_nodes[-1]
        x_offset = image_node.width - math_node.width
        math_node.location = image_node.location + (V((x_offset, -300)))

        links.new(value_node.outputs[0], math_node.inputs[1])
        links.new(math_node.outputs[0], disp_node.inputs[2])

    # Add texture coordinates
    coords_node = nodes.new("ShaderNodeTexCoord")
    coords_node.name = coords_node.label = "Coords"
    links.new(coords_node.outputs["UV"], anti_tiling_node.inputs[0])
    coords_node.location = anti_tiling_node.location - V((coords_node.width + 40, 0))

    # set position of optional nodes
    if hsv_node:
        hsv_node.location = diff_node.location + V((diff_node.width + 40, -110))

    if ao_mix_node:
        ao_mix_node.location = ao_image_node.location + V((ao_image_node.width + 40, 0))

    if rough_group_node:
        rough_group_node.location = rough_node.location + V((rough_node.width + 40, 0))

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
    # TODO: implement the append_reuse link method for objects
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
                raise KeyError(
                    f"Key {name} not found in collections {data_from.collections}\nIn blend file: {blend_file}"
                )

    for obj in bpy.data.objects:
        obj.select_set(False)

    collection: bpy.types.Collection = collection or data_to.collections[0]
    to_collection: bpy.types.Collection = get_ab_scene_settings(context).import_collection or context.collection
    if link:
        # Create an empty to use as an instance collection so that it can be moved by the user.
        empty = bpy.data.objects.new(collection.name, None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = collection
        to_collection.objects.link(empty)
        empty.empty_display_size = math.hypot(*list(collection.objects[0].dimensions))
        empty.select_set(True)
        final_obj = empty
        retval = empty
    else:
        to_collection.children.link(collection)

        # Set the selection
        final_obj = None
        for obj in collection.objects:
            obj.select_set(True)
            obj.name = f"{name}"
            final_obj = obj
        retval = collection

    context.view_layer.objects.active = final_obj

    # Give the nodes the correct names so that they can be edited in the N-panel.
    for obj in collection.objects:
        obj: Object
        for slot in obj.material_slots:
            if mat := slot.material:
                for node in mat.node_tree.nodes:
                    if node.bl_idname == "ShaderNodeNormalMap":
                        node.name = NODES.normal_map

    # Blender is weird, and without pushing an undo step
    # linking the object to the active collection will cause a crash.
    bpy.ops.ed.undo_push()
    return retval
