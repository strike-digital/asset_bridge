from pathlib import Path

ASSET_LIB_VERSION = (1, 0, 0)
PREVIEW_DOWNLOAD_TASK_NAME = "preview_download"


class Dirs():

    def __init__(self):
        self.addon = Path(__file__).parent
        self.asset_lists = self.addon / "asset_lists"
        self.previews = self.addon / "previews"


DIRS = Dirs()
