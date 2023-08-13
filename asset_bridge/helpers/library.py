import os
from pathlib import Path
from ..constants import ASSET_LIB_NAME, DIRS

import bpy


def is_lib_path_invalid(lib_path: Path) -> str:
    """Check if the given path is valid as an Asset Bridge library

    Returns:
        str: Empty string if path is valid, else an error message
    """
    if isinstance(lib_path, str):
        lib_path = Path(lib_path)

    if str(lib_path) == ".":
        return "Please select a downloads path"
    elif not lib_path.exists():
        return "Selected downloads path does not exist"
    elif not os.access(lib_path, os.W_OK):
        return "Insufficient permissions to use this directory"
    return ""


def ensure_bl_asset_library_exists():
    """Check that asset bridge blend is loaded as an asset library in blender, and if not, add it as one."""
    asset_libs = bpy.context.preferences.filepaths.asset_libraries
    for asset_lib in asset_libs:
        if asset_lib.path == str(DIRS.dummy_assets):
            break
    else:
        asset_lib = asset_libs.get(ASSET_LIB_NAME)
        if not asset_lib:
            bpy.ops.preferences.asset_library_add()
            asset_lib = asset_libs[-1]
            asset_lib = ASSET_LIB_NAME

        asset_lib = str(DIRS.dummy_assets)
        bpy.ops.wm.save_userpref()


sizes = ("", "KB", "MB", "GB", "TB")


def human_readable_file_size(num, suffix=""):
    """Stolen from stack overflow: https://stackoverflow.com/a/1094933/18864758"""

    # If the files are in Zetabytes, something has gone very wrong
    # for unit in ["", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
    for unit in sizes:
        if abs(num) < 1024.0:
            return f"{num:.0f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def get_dir_size(directory):
    """Get the total size of a directory in bytes."""
    total = 0
    if not Path(directory).exists():
        return total
    with os.scandir(directory) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total