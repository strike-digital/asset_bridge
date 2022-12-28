import os
from pathlib import Path


def is_lib_path_valid(lib_path: Path) -> str:
    """Check if the given path is valid as an Asset Bridge library

    Returns:
        str: Empty string if path is valid, else an error message
    """

    if str(lib_path) == ".":
        return "Please select a downloads path"
    elif not lib_path.exists():
        return "Selected downloads path does not exist"
    elif not os.access(lib_path, os.W_OK):
        return "Insufficient permissions to use this directory"
    return ""
