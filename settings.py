from threading import Thread

import bpy
from bpy.props import (BoolProperty, EnumProperty, IntProperty, PointerProperty, StringProperty)
from bpy.types import PropertyGroup, Scene
from .vendor import requests
from .constants import PREVIEWS_DIR
from .helpers import Asset, asset_list, get_icon, pcolls, singular

_selected_asset = None
loading_asset = False


class AssetBridgeSettings(PropertyGroup):

    show_asset_info: BoolProperty(
        name="Show asset info",
        description="Show extra info about this asset",
        default=False,
    )

    ui_import_progress: IntProperty(
        name="Downloading:",
        subtype="PERCENTAGE",
        min=0,
        max=100,
        get=lambda self: self.import_progress,
        set=lambda self, value: None,
    )

    progress = IntProperty(name="Downloading:", subtype="PERCENTAGE", min=0, max=100)

    import_progress: progress

    ui_preview_download_progress: IntProperty(
        name="Downloading:",
        subtype="PERCENTAGE",
        min=0,
        max=100,
        get=lambda self: self.preview_download_progress,
        set=lambda self, value: None,
    )

    preview_download_progress: progress

    def download_status_update(self, context):
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
        return items

    def sort_method_update(self, context):
        asset_list.sort(self.sort_method, self.sort_ascending)
        self.asset_name = list(self.get_assets())[0]

    sort_method: EnumProperty(items=sort_method_items, update=sort_method_update)

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
        update=lambda self, context: setattr(self, "filter_category", "ALL"),
    )

    def filter_category_items(self, context):
        items = [("ALL", "All", "All")]
        categories = list(getattr(asset_list, singular[self.filter_type] + "_categories"))
        categories.sort()
        for cat in categories:
            items.append((cat, cat.title(), f"Only show assets in the category '{cat}'"))
        return items

    filter_category: EnumProperty(
        items=filter_category_items,
        name="Asset categories",
        description="Filter the asset list on only show a specific category",
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
                image_path = PREVIEWS_DIR / (name + ".png")
                icon_id = pcoll.load(name, str(image_path), path_type="IMAGE").icon_id
            items.append((name, data["name"], data["name"], icon_id, i))

        # Show not found icon
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
        else:
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
                # _selected_asset = Asset(self.asset_name)
            else:
                return None

    selected_asset: Asset = property(get_selected_asset)

    def get_asset_quality_items(self, context):
        items = []
        if self.asset_name == "NONE":
            return [("1k", "1k", "1k")]
        if self.selected_asset:
            quality_levels = self.selected_asset.get_quality_dict()
            for q in sorted(quality_levels.keys(), key=lambda q: int(q[:-1])):
                items.append((q, q, f"Load this asset at {q} resolution."))
        return items

    def get_asset_quality(self):
        maximum = len(self.get_asset_quality_items(bpy.context))
        quality = self.get("_asset_quality", 0)
        return min(quality, maximum - 1)

    def set_asset_quality(self, value):
        self["_asset_quality"] = value

    asset_quality: EnumProperty(items=get_asset_quality_items, get=get_asset_quality, set=set_asset_quality)

    reload_asset: BoolProperty(
        name="Redownload asset files",
        description="Whether to redownload the assets files from the internet when it is imported",
    )

    # Info section

    def info_categories_items(self, context):
        return [(c, c, c) for c in self.selected_asset.categories]

    def info_categories_get(self):
        return -1

    def info_categories_set(self, value):
        asset_name = self.asset_name
        self.filter_category = self.selected_asset.categories[value]
        self.asset_name = asset_name

    info_categories: EnumProperty(
        items=info_categories_items,
        get=info_categories_get,
        set=info_categories_set,
    )

    def info_tags_items(self, context):
        return [(t, t, t) for t in self.selected_asset.tags]

    def info_tags_set(self, value):
        asset_name = self.asset_name
        self.filter_search = self.selected_asset.tags[value]
        self.asset_name = asset_name

    info_tags: EnumProperty(
        items=info_tags_items,
        get=lambda self: -1,
        set=info_tags_set,
    )

    def info_authors_items(self, context):
        return [(a, a, a) for a in self.selected_asset.authors]

    def info_authors_set(self, value):
        author = list(self.selected_asset.authors)[value]
        data = requests.get(f"https://api.polyhaven.com/author/{author}").json()
        if "link" in data:
            link = data["link"]
        elif "email" in data:
            link = "mailto:" + data["email"]
        else:
            return
        bpy.ops.wm.url_open(url=link)

    info_authors: EnumProperty(
        items=info_authors_items,
        get=lambda self: -1,
        set=info_authors_set,
    )


def depsgraph_update_pre_handler(scene: Scene, _):
    remove = []
    for obj in scene.objects:
        if obj.is_asset_bridge:
            if tuple(obj.location) == (0., 0., 0.):
                continue
            asset = Asset(obj.asset_bridge_name)
            # asset.download_asset(bpy.context)
            asset.import_asset(bpy.context, location=obj.location)

            asset_objs = [obj for obj in scene.objects if obj.select_get()]
            remove.append(obj)

    for obj in remove:
        bpy.data.objects.remove(obj)


def register():
    bpy.types.Scene.asset_bridge = PointerProperty(type=AssetBridgeSettings)
    bpy.types.Object.is_asset_bridge = BoolProperty()
    bpy.types.Object.asset_bridge_name = bpy.props.StringProperty()
    bpy.app.handlers.depsgraph_update_pre.append(depsgraph_update_pre_handler)


def unregister():
    del bpy.types.Scene.asset_bridge
    del bpy.types.Object.is_asset_bridge
    del bpy.types.Object.asset_bridge_name
    for handler in bpy.app.handlers.depsgraph_update_pre:
        if handler.__name__ == depsgraph_update_pre_handler.__name__:
            bpy.app.handlers.depsgraph_update_pre.remove(handler)
