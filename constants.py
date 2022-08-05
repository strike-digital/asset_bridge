from pathlib import Path

BASE_ASSET_NAME = "__base_asset__"

ADDON_DIR = Path(__file__).parent
PREVIEWS_DIR = ADDON_DIR / "previews"
DOWNLOADS_DIR = ADDON_DIR / "downloads"
SCRIPTS_DIR = ADDON_DIR / "scripts"

DIRS = {
    "previews": PREVIEWS_DIR,
    "downloads": DOWNLOADS_DIR,
    "scripts": SCRIPTS_DIR,
    "hdris": DOWNLOADS_DIR / "hdris",
    "textures": DOWNLOADS_DIR / "textures",
    "texture_textures": DOWNLOADS_DIR / "textures" / "textures",
    "models": DOWNLOADS_DIR / "models",
    "model_textures": DOWNLOADS_DIR / "models" / "textures",
}

FILES = {
    "setup_asset_library": SCRIPTS_DIR / "setup_asset_library.py",
    "asset_lib_blend": ADDON_DIR / "asset_lib.blend",
}
FILE_NAMES = {k: v.name for k, v in FILES.items()}
FILES_RELATIVE = {k: Path(str(v).removeprefix(str(ADDON_DIR))) for k, v in FILES.items()}