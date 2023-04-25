from pathlib import Path
from typing import Dict
from bpy.types import ImagePreview as P
from bpy.utils import previews
from .constants import DIRS

preview_collections: Dict[str, Dict[str, P]] = {}


def get_icon(name: str) -> P:
    return preview_collections["icons"][name].icon_id


class Icons():

    # These need to be properties as the preview collection isn't fill until register time
    ab_twitter: int = property(lambda _: get_icon("ab_twitter"))
    ab_blender_artists: int = property(lambda _: get_icon("ab_blender_artists"))
    ab_blender_market: int = property(lambda _: get_icon("ab_blender_market"))
    ab_review: int = property(lambda _: get_icon("ab_review"))


ICONS = Icons()


def load_icon(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Could not load file '{path}' as it doesn't exist")
    coll = preview_collections.get("icons")
    if not coll:
        coll = previews.new()
    coll.load(path.stem, str(path), "IMAGE")
    preview_collections["icons"] = coll


def register():
    for f in DIRS.icons.iterdir():
        load_icon(f)


def unregister():
    for coll in preview_collections.values():
        coll.close()