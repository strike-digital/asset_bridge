from pathlib import Path

ASSET_LIB_VERSION = (1, 0, 0)


class Dirs():

    def __init__(self):
        self.package = Path(__file__).parent
        self.asset_lists = self.package / "asset_lists"


DIRS = Dirs()
