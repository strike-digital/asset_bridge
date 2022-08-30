from threading import Thread

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty, FloatVectorProperty)
from bpy.types import PropertyGroup
from .constants import __IS_DEV__, DIRS
from .helpers import get_icon, get_prefs, pcolls
from .assets import singular
from .assets import Asset, asset_list

_selected_asset = None
loading_asset = False


def add_progress(cls, name):
    """Add a two properties to the given class; one that can be set by the addon, and one that can be shown in the UI
    This allows for a standard progress look across the addon."""
    kwargs = {"name": "Downloading:", "subtype": "PERCENTAGE", "min": 0, "max": 100, "precision": 0}
    cls.__annotations__[name] = FloatProperty(**kwargs)
    ui_kwargs = kwargs.copy()
    ui_kwargs["set"] = lambda self, value: None
    ui_kwargs["get"] = lambda self: getattr(self, name)
    cls.__annotations__[f"ui_{name}"] = FloatProperty(**ui_kwargs)


class SharedSettings():
    pass


add_progress(SharedSettings, "import_progress")


class PanelSettings(PropertyGroup, SharedSettings):
    __reg_order__ = 0

    show_asset_info: BoolProperty(
        name="Show asset info",
        description="Show extra info about this asset",
        default=False,
    )

    show_import_settings: BoolProperty(
        name="Show import settings",
        description="Show extra settings for importing",
        default=False,
    )

    def download_status_update(self, context):
        return
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

    download_status: EnumProperty(
        items=[
            ("NONE", "None", "Not downloading currently"),
            ("DOWNLOADING_ASSET", "Downloading", "Downloading the asset from the internet"),
            ("DOWNLOADING_PREVIEWS", "Downloading previews", "Downloading all previews"),
        ],
        update=download_status_update,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def sort_method_items(self, context):
        items = [
            ("NAME", "Name", "Sort assets alphabetically", "SORTALPHA", 0),
            ("DOWNLOADS", "Downloads", "Sort assets by number of downloads", "IMPORT", 1),
            ("DATE", "Date", "Sort assets by publishing date", "TIME", 2),
        ]
        if self.filter_type == "hdris":
            items.append(("EVS", "EVs", "Sort assets by exposure range", "LIGHT_SUN", len(items)))
        elif self.filter_type == "textures":
            items.append((
                "DIMENSIONS",
                "Dimensions",
                "Sort assets by the real world size of the textures",
                "MOD_LENGTH",
                len(items),
            ))
        return items

    def sort_method_update(self, context):
        asset_list.sort(self.sort_method, self.sort_ascending)
        self.asset_name = list(self.get_assets())[0]
        context.region.tag_redraw()

    def sort_method_get(self):
        return min(self.get("_sort_method", 0), len(self.sort_method_items(bpy.context)) - 1)

    def sort_method_set(self, value):
        self["_sort_method"] = value

    sort_method: EnumProperty(
        items=sort_method_items,
        update=sort_method_update,
        get=sort_method_get,
        set=sort_method_set,
    )

    sort_order: EnumProperty(
        items=[
            ("ASC", "Ascending", "Sort assets in from lowest to highest", "SORT_DESC", 0),
            ("DESC", "Descending", "Sort assets in from highest to lowest", "SORT_ASC", 1),
        ],
        default="DESC",
        update=sort_method_update,
    )
    sort_ascending: BoolProperty(get=lambda self: self.sort_order == "ASC")

    filter_type: EnumProperty(
        items=[
            ("all", "All assets", "show all assets", "ASSET_MANAGER", 0),
            ("hdris", "HDRIs", "Only show HDRI assets", "WORLD", 1),
            ("textures", "Materials", "Only show material assets", "TEXTURE", 2),
            ("models", "Models", "Only show model assets", "MESH_MONKEY", 3),
        ],
        name="Asset type",
        description="Filter the asset list on only show a specific type",
        default="hdris",
        update=lambda self, context: setattr(self, "filter_category", "ALL"),
    )

    def filter_category_items(self, context):
        items = [("ALL", "All", "All")]
        categories = sorted(getattr(asset_list, f"{singular[self.filter_type]}_categories"))
        items.extend((cat, cat.title(), f"Only show assets in the category '{cat}'") for cat in categories)
        return items

    filter_category: EnumProperty(
        items=filter_category_items,
        name="Asset categories",
        description="Filter the asset list on only show a specific category",
        update=lambda self, context: self.sort_method_update(context),
    )

    filter_search: StringProperty(
        name="Search",
        description="Search assets based on whether the query is contain in the name or tags",
        options={"TEXTEDIT_UPDATE", "HIDDEN"},
    )

    def get_assets(self):
        items = {}
        assets = getattr(asset_list, self.filter_type)
        search = self.filter_search.lower()
        category = self.filter_category
        for name, data in assets.items():
            if search not in data["name"].lower() and search not in "@".join(
                    data["tags"]) or (category not in data["categories"] if category != "ALL" else False):
                continue

            items[name] = data
        global asset_len
        asset_len = len(items)
        return items

    def get_asset_name_items(self, context):
        items = []
        assets = self.get_assets()
        pcoll = pcolls["assets"]
        for i, (name, data) in enumerate(assets.items()):
            if name in pcoll:
                icon_id = pcoll[name].icon_id
            else:
                image_path = DIRS.previews / f"{name}.png"
                icon_id = pcoll.load(name, str(image_path), path_type="IMAGE").icon_id
            items.append((name, data["name"], data["name"], icon_id, i))
        if not items:
            items.append(("NONE", "", "", get_icon("not_found").icon_id, self.get_asset_name()))
        return items

    def get_asset_name(self):
        name = self.get("_asset_name", 0)
        maximum = len(self.get_assets())
        return min(name, maximum - 1)

    def set_asset_name(self, value):
        self["_asset_name"] = value

    asset_name: EnumProperty(items=get_asset_name_items, get=get_asset_name, set=set_asset_name)

    def get_selected_asset(self):
        global _selected_asset
        global loading_asset
        if self.asset_name == "NONE":
            return None
        if _selected_asset and self.asset_name == _selected_asset.name or loading_asset:
            return _selected_asset

        if self.asset_name:
            loading_asset = True

            def get_asset_info():
                """Load the asset info from the internet in another thread"""
                global loading_asset
                global _selected_asset
                _selected_asset = Asset(self.asset_name)
                loading_asset = False

            thread = Thread(target=get_asset_info)
            thread.start()
        else:
            return None

    selected_asset: Asset = property(get_selected_asset)

    def get_asset_quality_items(self, context):
        items = []
        if self.asset_name == "NONE":
            return [("1k", "1k", "1k")]
        if self.selected_asset:
            quality_levels = self.selected_asset.get_quality_dict()
            levels = sorted(quality_levels.keys(), key=lambda q: int(q[:-1]))
            items.extend((q, q, f"Load this asset at {q} resolution.") for q in levels)

        return items

    def get_asset_quality(self):
        maximum = len(self.get_asset_quality_items(bpy.context))
        quality = self.get("_asset_quality", 0)
        return min(quality, maximum - 1)

    def set_asset_quality(self, value):
        self["_asset_quality"] = value

    asset_quality: EnumProperty(items=get_asset_quality_items, get=get_asset_quality, set=set_asset_quality)

    # Import settings

    import_method: EnumProperty(
        items=[
            (
                "APPEND",
                "Append",
                "\n".join(("Append the assets directly into the file (this can cause the file size to grow quickly,",
                           "but allows more control over the asset data)")),
                "UNLINKED",
                0,
            ),
            (
                "LINK",
                "Link",
                "\n".join(("Link the asset data from the downloaded file.",
                           "This keeps file size low, but doesn't allow as much control over the asset data")),
                "LINKED",
                1,
            ),
        ],
        name="Import method",
        description="How to import the downloaded assets into the current file.",
    )


add_progress(PanelSettings, "preview_download_progress")


class BrowserSettings(PropertyGroup, SharedSettings):
    __reg_order__ = 0


class AssetBridgeSettings(PropertyGroup, SharedSettings):
    __reg_order__ = 1

    panel: PointerProperty(type=PanelSettings)

    browser: PointerProperty(type=BrowserSettings)

    mouse_pos: FloatVectorProperty(size=2)


def register():
    bpy.types.Scene.asset_bridge = PointerProperty(type=AssetBridgeSettings)
    # bpy.types.Scene.asset_bridge.panel = PointerProperty(type=PanelSettings)
    bpy.types.World.is_asset_bridge = BoolProperty()
    bpy.types.World.asset_bridge_name = StringProperty()
    bpy.types.Material.is_asset_bridge = BoolProperty()
    bpy.types.Material.asset_bridge_name = StringProperty()
    bpy.types.Object.is_asset_bridge = BoolProperty()
    bpy.types.Object.asset_bridge_name = StringProperty()

    prefs = get_prefs(bpy.context)
    if __IS_DEV__:
        prefs.lib_path = "D:\\Documents\\Blender\\addons\\AA Own addons\\Asset Bridge\\Asset Bridge Downloads\\"
    else:
        prefs.lib_path = prefs.lib_path


def unregister():
    del bpy.types.Scene.asset_bridge
    del bpy.types.Object.is_asset_bridge
    del bpy.types.Object.asset_bridge_name
