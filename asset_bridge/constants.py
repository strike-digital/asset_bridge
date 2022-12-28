from pathlib import Path
from .helpers.prefs import get_prefs
import bpy

ASSET_LIB_VERSION = (1, 0, 0)
PREVIEW_DOWNLOAD_TASK_NAME = "preview_download"


# I know this isn't really a constant, but hey, sue me.
class Dirs():

    def __init__(self):
        self.addon = Path(__file__).parent
        self.asset_lists = self.addon / "asset_lists"
        self.previews = self.addon / "previews"

        # We need the context to create these, so run them in a timer.
        bpy.app.timers.register(self.update)

    def update(self):
        self.library = Path(get_prefs(bpy.context).lib_path)


DIRS = Dirs()
