from pathlib import Path
from .helpers.prefs import get_prefs
import bpy

ASSET_LIB_VERSION = (1, 0, 0)
PREVIEW_DOWNLOAD_TASK_NAME = "preview_download"


# I know this isn't really a constant, but hey, sue me.
class Dirs():

    addon = Path(__file__).parent
    asset_lists = addon / "asset_lists"
    previews = addon / "previews"
    scripts = addon / "scripts"

    # We need the context to create these, so run them in a timer.
    def update(self):
        self.library = Path(get_prefs(bpy.context).lib_path)

    bpy.app.timers.register(update)


class Files():

    script_create_dummy_assets = Dirs.scripts / "create_dummy_assets.py"


DIRS = Dirs()
FILES = Files()
