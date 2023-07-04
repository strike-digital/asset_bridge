import json
from pathlib import Path

import bpy

from .helpers.prefs import get_prefs

# This should be changed during the build process in build.py
__IS_DEV__ = True
ASSET_LIB_VERSION = (1, 0, 0)
ASSET_LIB_NAME = "Asset Bridge"
PREVIEW_DOWNLOAD_TASK_NAME = "preview_download"
CHECK_NEW_ASSETS_TASK_NAME = "check_new_assets"
AB_COLLECTION_NAME = "Asset Bridge assets"


# Custom web response errors
class ServerError503(Exception):
    """Returned when a server is temporarily down, potentially for maintenance or because of capacity issues."""

    def __init__(self, url, message=""):
        if not message:
            message = f"The server couldn't fulfill the request for {url}"
        super().__init__(message)


class AssetVersions():
    """The import version of an asset, used for versioning.
    The order is (Breaking, Important, Minor)."""

    material = (1, 0, 0)
    model = (1, 0, 0)
    hdri = (1, 0, 0)


ASSET_VERSIONS = AssetVersions()


# The names of useful node groups.
# I'm now realising that these should probably be enums, but I don't care enough to change it.
class NodeGroups():

    anti_tiling = "AB-anti_tiling"
    roughness_map = "AB-roughness_map"
    hdri_coords = "AB-hdri_coords"
    hdri_color = "AB-hdri_color"
    normal_map = "AB-normal_map"


class NodeNames():

    anti_tiling = "AB-anti_tiling"
    mapping = "AB-mapping"
    ao_mix = "AB-ao_mix"
    hsv = "AB-hsv"
    roughness = "AB-roughness"
    normal_map = "AB-normal_map"
    displacement = "AB-displacement"
    displacement_strength = "AB-displacement_strength"
    scale = "AB-scale"
    opacity = "AB-opacity"
    temp_output = "AB-temp_output"


NODE_GROUPS = NodeGroups()
NODES = NodeNames()


# I know this isn't really a constant, but hey, sue me.
class Dirs():

    addon = Path(__file__).parent
    cache = addon / "cache"
    previews = cache / "previews"
    high_res_previews = cache / "high_res_previews"
    scripts = addon / "scripts"
    resources = addon / "resources"
    icons = resources / "icons"

    # We need the context to create these, so run them in a timer.
    def update(self, lib_path: Path = None):
        if not lib_path:
            return
        self.library = Path(lib_path) if lib_path is not None else Path(get_prefs(bpy.context).lib_path)
        self.assets = self.library / "assets"
        self.dummy_assets = self.library / "dummy_assets"
        FILES.update()

        all_paths = [v for v in (self.__dict__ | self.__class__.__dict__).values() if isinstance(v, Path)]
        for dir in all_paths:
            dir.mkdir(parents=True, exist_ok=True)

        # Recache the new path
        with open(FILES.prefs, "w") as f:
            json.dump({"lib_path": str(self.library)}, f, indent=2)


class Files():

    script_create_dummy_assets = Dirs.scripts / "sc_create_dummy_assets.py"
    resources_blend = Dirs.resources / "resources.blend"
    prefs = Dirs.cache / "prefs.json"
    log = Dirs.cache / "log.txt"

    def update(self, lib_path: Path = ""):
        lib = lib_path or DIRS.library
        self.lib_info = lib / "lib_info.json"
        # Sometimes this is initialized without the DIRS being updated, when changing the lib_path
        if hasattr(DIRS, "dummy_assets"):
            self.lib_progress = DIRS.dummy_assets / "progress.json"
        return self


DIRS = Dirs()
FILES = Files()

if FILES.prefs.exists():
    # We need to initially load the path from the cached file, as we don't have access to the addon preferences at register
    with open(FILES.prefs, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"lib_path": ""}

        DIRS.update(lib_path=data["lib_path"])
else:
    DIRS.update(lib_path="")
