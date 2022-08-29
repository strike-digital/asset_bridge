from pathlib import Path
from uuid import uuid4

CATALOG_HEADER = """\
# This is an Asset Catalog Definition file for Blender.
#
# Empty lines and lines starting with `#` will be ignored.
# The first non-ignored line should be the version indicator.
# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"

VERSION 1

"""


class AssetCatalogFile():

    def __init__(self, catalog_dir):
        self.catalog_file = Path(catalog_dir) / "blender_assets.cats.txt"
        self.ensure_exists()
        self.update_catalogs()

    def __getitem__(self, name):
        return self.catalogs[name]

    def ensure_exists(self):
        if not self.catalog_file.exists():
            with open(self.catalog_file, "w") as f:
                f.write(CATALOG_HEADER)

    def update_catalogs(self):
        self.catalogs = self.get_catalogs()

    def get_catalogs(self):
        catalogs = {}
        with open(self.catalog_file, "r") as f:
            for line in f.readlines():
                if line.startswith(("#", "VERSION", "\n")):
                    continue
                catalog = AssetCatalog(*line.split(":"))
                catalogs[catalog.path] = catalog
        return catalogs

    def reset(self):
        with open(self.catalog_file, "w") as f:
            f.write(CATALOG_HEADER)
        self.update_catalogs()

    def add_catalog(self, name, path: str = "", uuid: str = ""):
        uuid = uuid or str(uuid4())
        path = path or name
        with open(self.catalog_file, "a") as f:
            f.write(f"{uuid}:{path}:{name}\n")
        self.update_catalogs()

    def remove_catalog(self, path):
        catalog = self.catalogs[path]
        with open(self.catalog_file, "r") as f:
            lines = f.readlines()
        with open(self.catalog_file, "w") as f:
            for line in lines:
                if line == str(catalog):
                    continue
                f.write(line)

    def ensure_catalog_exists(self, name, path=""):
        path = path or name
        if name not in self.catalogs:
            self.add_catalog(name, path)


class AssetCatalog():

    def __init__(self, uuid, path, name):
        self.uuid = uuid
        self.path = path
        self.name = name

    def __str__(self):
        return ":".join([self.uuid, self.path, self.name])
