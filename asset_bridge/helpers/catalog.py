from __future__ import annotations
from pathlib import Path
from typing import Dict
from uuid import uuid4

"""A module for working with blender_assets.cats.txt files, and the asset catalogs that they contain"""


CATALOG_HEADER = """\
# This is an Asset Catalog Definition file for Blender.
#
# Empty lines and lines starting with `#` will be ignored.
# The first non-ignored line should be the version indicator.
# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"

VERSION 1

"""


class AssetCatalog():

    def __init__(self, uuid, path, name):
        self.uuid = uuid
        self.path = path
        self.name = name

    def __str__(self):
        return ":".join([self.uuid, self.path, self.name])


class AssetCatalogFile():
    """Represents a file containing the catalog info for a blender asset library."""

    def __init__(self, catalog_dir, filename="", load_from_file=True):
        # By default, use the normal catalog file name, but can also use a custom one
        self.catalog_file = Path(catalog_dir) / (filename or "blender_assets.cats.txt")
        self.catalogs = {}
        self.ensure_exists()
        if load_from_file:
            self.update_catalog_from_file()

    def __getitem__(self, name) -> AssetCatalog:
        return self.catalogs[name]

    def write(self):
        """Update the catalog file on the disk"""
        with open(self.catalog_file, "w") as f:
            f.write(CATALOG_HEADER)
            for catalog in self.catalogs.values():
                f.write(f"{catalog.uuid}:{catalog.path}:{catalog.name}\n")

    def merge(self, other_catalog: AssetCatalogFile):
        """Combine two AssetCatalogFile objects, merging all entries"""
        self.catalogs.update(other_catalog.catalogs)

    def ensure_exists(self):
        """Ensure that this catalog file exists"""
        if not self.catalog_file.exists():
            with open(self.catalog_file, "w") as f:
                f.write(CATALOG_HEADER)

    def update_catalog_from_file(self):
        """Read and set the catalogs from the file"""
        self.catalogs = self.get_catalogs()

    def get_catalogs(self) -> Dict[str, AssetCatalog]:
        """Read the catalogs from the file"""
        catalogs = {}
        with open(self.catalog_file, "r") as f:
            for line in f.readlines():
                if line.startswith(("#", "VERSION", "\n")):
                    continue
                catalog = AssetCatalog(*line.split(":")[:4])
                catalogs[catalog.path] = catalog
        return catalogs

    def reset(self):
        """Remove all catalogs"""
        self.catalogs = {}

    def add_catalog(self, name, path: str = "", uuid: str = ""):
        """Add a catalog"""
        uuid = uuid or str(uuid4())
        path = path or name

        self.catalogs[path] = AssetCatalog(uuid, path, name)

    def remove_catalog(self, path):
        """Remove a catalog"""
        del self.catalogs[path]

    def ensure_catalog_exists(self, name, path=""):
        """Ensure that a catalog exists, and if it doesn't, create one."""
        path = path or name
        if name not in self.catalogs:
            self.add_catalog(name, path)
