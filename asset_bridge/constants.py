import json
import os
from pathlib import Path

__IS_DEV__ = True

ASSET_LIB_VERSION = (1, 0, 0)
BASE_ASSET_NAME = "__base_asset__"
BL_ASSET_LIB_NAME = "Asset Bridge"


# I know this isn't really a constant, but hey, sue me.
class Dirs():

    def __init__(self):
        self.addon = addon_dir = Path(__file__).parent
        self.previews = addon_dir / "previews"
        self.scripts = addon_dir / "scripts"
        self.icons = addon_dir / "icons"

        # We can't access the addon preferences at init, so save the lib path in a file.
        with open(self.addon / "prefs.json", "r") as f:
            prefs = json.load(f)
        print("init", prefs["lib_path"])
        self.update(Path(prefs["lib_path"]))

    @property
    def all_dirs(self):
        return [v for v in (self.__dict__).values() if isinstance(v, Path)]

    def check_lib_path_invalid(self, lib_path: Path):
        if str(lib_path) == ".":
            return "Please select a downloads path"
        elif not lib_path.exists():
            return "Selected downloads path does not exist"
        elif not os.access(lib_path, os.W_OK):
            return "Insufficient permissions to use this directory"
        return ""

    def update(self, lib_path):
        """Update the directories to be relative to the given library path"""
        lib_path = Path(lib_path)
        self.is_valid = True
        self.invalid_message = ""
        self.library = lib_path
        self.hdris = lib_path / "hdris"
        self.textures = lib_path / "textures"
        self.texture_textures = self.textures / "textures"
        self.models = lib_path / "models"
        self.model_textures = self.models / "textures"
        print("lib path", lib_path)
        if hasattr(self, "files"):
            self.files.update(lib_path)
        else:
            self.files = Files(self)

        if message := self.check_lib_path_invalid(lib_path):
            self.is_valid = False
            self.invalid_message = message
            return

        for dir in self.all_dirs:
            try:
                dir.mkdir()
            except FileExistsError:
                pass


class Files():

    def __init__(self, dirs: Dirs):
        self.dirs = dirs
        self.asset_list = dirs.addon / "asset_list.json"
        self.setup_asset_library = dirs.scripts / "setup_asset_library.py"
        self.setup_model_blend = dirs.scripts / "setup_model_blend.py"
        self.asset_lib_blend = dirs.addon / "asset_lib.blend"
        self.prefs_file = dirs.addon / "prefs.json"
        if dirs.is_valid:
            self.update(dirs.library)

    @property
    def all_files(self):
        return [v for v in (self.__dict__).values() if isinstance(v, Path)]

    def update(self, lib_path):
        print("update", lib_path)
        lib_path = Path(lib_path)
        self.lib_info = lib_path / "lib_info.json"
        self.asset_lib_blend = lib_path / "asset_lib.blend"


DIRS = Dirs()
FILES = DIRS.files

# FILES = {
#     "asset_list": ADDON_DIR / "asset_list.json",
#     "setup_asset_library": SCRIPTS_DIR / "setup_asset_library.py",
#     "setup_model_blend": SCRIPTS_DIR / "setup_model_blend.py",
#     "asset_lib_blend": ADDON_DIR / "asset_lib.blend",
# }
# FILE_NAMES = {k: v.name for k, v in FILES.items()}
# FILES_RELATIVE = {k: Path(str(v).removeprefix(str(ADDON_DIR))) for k, v in FILES.items()}
# FILES_RELATIVE = {k: v.relative_to(ADDON_DIR) for k, v in FILES.items()}
