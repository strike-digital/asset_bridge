import bpy
from pathlib import Path

__IS_DEV__ = True

BASE_ASSET_NAME = "__base_asset__"
BL_ASSET_LIB_NAME = "Asset Bridge"

ADDON_DIR = Path(__file__).parent
PREVIEWS_DIR = ADDON_DIR / "previews"
SCRIPTS_DIR = ADDON_DIR / "scripts"
ICONS_DIR = ADDON_DIR / "icons"


# I know this isn't really a constant, but hey, sue me.
class Dirs():

    previews = ADDON_DIR / "previews"
    scripts = ADDON_DIR / "scripts"
    icons = ADDON_DIR / "icons"
    library: Path
    hdris: Path
    textures: Path
    texture_textures: Path
    models: Path
    model_textures: Path

    def __init__(self):
        self.update(ADDON_DIR)

    def update(self, lib_path):
        """Update the directories to be relative to the given library path"""
        lib_path = Path(lib_path)
        if str(lib_path) == "." or not lib_path.exists():
            lib_path = ADDON_DIR
        self.library = lib_path
        self.hdris = lib_path / "hdris"
        self.textures = lib_path / "textures"
        self.texture_textures = self.textures / "textures"
        self.models = lib_path / "models"
        self.model_textures = self.models / "textures"

        for dir in [v for v in self.__dict__.values() if isinstance(v, Path)]:
            try:
                dir.mkdir()
            except FileExistsError:
                pass


DIRS = Dirs()

FILES = {
    "asset_list": ADDON_DIR / "asset_list.json",
    "setup_asset_library": SCRIPTS_DIR / "setup_asset_library.py",
    "asset_lib_blend": ADDON_DIR / "asset_lib.blend",
}
FILE_NAMES = {k: v.name for k, v in FILES.items()}
FILES_RELATIVE = {k: Path(str(v).removeprefix(str(ADDON_DIR))) for k, v in FILES.items()}


def register():

    def get_prefs(context: bpy.types.Context) -> bpy.types.AddonPreferences:
        return context.preferences.addons[__package__].preferences

    def update_dirs():
        prefs = get_prefs(bpy.context)
        if __IS_DEV__:
            prefs.lib_path = "D:\\Documents\\Blender\\addons\\AA Own addons\\Asset Bridge\\Asset Bridge Downloads\\"
        else:
            prefs.lib_path = prefs.lib_path

    bpy.app.timers.register(update_dirs, first_interval=.0)