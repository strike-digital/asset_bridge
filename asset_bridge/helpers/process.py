from pathlib import Path
import subprocess
import bpy


def new_blender_process(
    script: Path,
    script_args: list = None,
    factory: bool = True,
    background: bool = True,
) -> subprocess.Popen:
    """Create a new blender process and return a reference to it"""

    if script_args is None:
        script_args = []
    args = []
    if factory:
        args.append("--factory-startup")
    if background:
        args.append("-b")

    return subprocess.Popen([bpy.app.binary_path, *args, "--python", script, "--", *script_args],)