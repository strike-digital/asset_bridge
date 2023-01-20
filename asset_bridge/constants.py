import json
from pathlib import Path
from .helpers.prefs import get_prefs
import bpy

# This should be changed during the build process in build.py
__IS_DEV__ = True
ASSET_LIB_VERSION = (1, 0, 0)
ASSET_LIB_NAME = "Asset Bridge"
PREVIEW_DOWNLOAD_TASK_NAME = "preview_download"


# The names of useful node groups
class NodeGroups():

    anti_tiling = "AB-anti_tiling"
    hdri_coords = "AB-hdri_coords"
    hdri_color = "AB-hdri_color"


class NodeNames():

    anti_tiling = "AB-anti_tiling"
    mapping = "AB-mapping"
    ao_mix = "AB-ao_mix"
    normal_map = "AB-normal_map"
    displacement = "AB-displacement"
    displacement_strength = "AB-displacement_strength"
    scale = "AB-scale"


NODE_GROUPS = NodeGroups()
NODES = NodeNames()


# I know this isn't really a constant, but hey, sue me.
class Dirs():

    addon = Path(__file__).parent
    asset_lists = addon / "asset_lists"
    previews = addon / "previews"
    scripts = addon / "scripts"
    resources = addon / "resources"

    # We need the context to create these, so run them in a timer.
    def update(self, lib_path: Path = None):
        self.library = Path(lib_path) if lib_path is not None else Path(get_prefs(bpy.context).lib_path)
        self.assets = self.library / "assets"
        self.dummy_assets = self.library / "dummy_assets"
        FILES.update()

        all_paths = [v for v in (self.__dict__).values() if isinstance(v, Path)]
        for dir in all_paths:
            dir.mkdir(parents=True, exist_ok=True)

        # Recache the new path
        with open(FILES.prefs, "w") as f:
            json.dump({"lib_path": str(self.library)}, f, indent=2)


class Files():

    script_create_dummy_assets = Dirs.scripts / "create_dummy_assets.py"
    resources_blend = Dirs.resources / "resources.blend"
    prefs = Dirs.addon / "prefs.json"

    def update(self, lib_path: Path = ""):
        lib = lib_path or DIRS.library
        self.lib_info = lib / "lib_info.json"
        self.lib_progress = DIRS.dummy_assets / "progress.json"
        return self


DIRS = Dirs()
FILES = Files()

# We need to initially load the path from the cached file, as we don't have access to the addon preferences at register
with open(FILES.prefs, "r") as f:
    try:
        data = json.load(f)
    except json.JSONDecodeError:
        data = {"lib_path": ""}

    DIRS.update(lib_path=data["lib_path"])
