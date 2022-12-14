from pathlib import Path
import subprocess
import traceback
from types import TracebackType
import bpy


def new_blender_process(
    script: Path,
    script_args: list = None,
    file: Path = None,
    factory: bool = True,
    background: bool = True,
    use_stdout: bool = True,
) -> subprocess.Popen:
    """Create a new blender process and return a reference to it"""

    if script_args is None:
        script_args = []
    else:
        script_args = list(script_args)
        script_args.insert(0, "--")
    args = []
    if file:
        args.append(str(file))
    if factory:
        args.append("--factory-startup")
    if background:
        args.append("-b")

    kwargs = {"stdout": subprocess.PIPE} if use_stdout else {}

    return subprocess.Popen([bpy.app.binary_path, *args, "--python-exit-code", "1", "--python", script, *script_args], **kwargs)


def format_traceback(traceback_object: TracebackType) -> str:
    """Format a traceback object into a string"""
    return ''.join(traceback.format_exception(None, traceback_object, traceback_object.__traceback__))
