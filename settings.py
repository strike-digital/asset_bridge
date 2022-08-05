import bpy
from threading import Thread
from bpy.props import BoolProperty, EnumProperty, PointerProperty, IntProperty
from bpy.types import PropertyGroup
from .constants import PREVIEWS_DIR
from .helpers import Asset, asset_list, pcolls

_selected_asset = None
loading_asset = False


class AssetBridgeSettings(PropertyGroup):

    ui_import_progress: IntProperty(
        name="Downloading:",
        subtype="PERCENTAGE",
        min=0,
        max=100,
        get=lambda self: self.import_progress,
        set=lambda self, value: None,
    )

    import_progress: IntProperty(name="Downloading:", subtype="PERCENTAGE", min=0, max=100)

    def import_stage_update(self, context):
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

    import_stage: EnumProperty(
        items=[
            ("NONE", "None", "Not downloading currently"),
            ("DOWNLOADING", "Downloading", "Downloading the asset from the internet"),
            ("IMPORTING", "Importing", "Importing the asset from a file"),
        ],
        update=import_stage_update,
    )

    filter_type: EnumProperty(
        items=[
            ("all", "All assets", "show all assets", "ASSET_MANAGER", 0),
            ("hdris", "HDRIs", "Only show HDRI assets", "WORLD", 1),
            ("textures", "Materials", "Only show material assets", "TEXTURE", 2),
            ("models", "Models", "Only show model assets", "MESH_MONKEY", 3),
        ],
        name="Asset type",
        description="Filter the asset list on only show a specific type",
    )

    def get_asset_name_items(self, context):
        items = []
        assets = getattr(asset_list, self.filter_type)
        pcoll = pcolls["assets"]
        for i, (name, data) in enumerate(list(assets.items())[:]):
            if name in pcoll:
                icon_id = pcoll[name].icon_id
            else:
                image_path = PREVIEWS_DIR / (name + ".png")
                icon_id = pcoll.load(name, str(image_path), path_type="IMAGE").icon_id
            items.append((name, data["name"], data["name"], icon_id, i))
        return items

    def get_asset_name(self):
        name = self.get("_asset_name", 0)
        maximum = len(getattr(asset_list, self.filter_type))
        return min(name, maximum - 1)

    def set_asset_name(self, value):
        self["_asset_name"] = value

    asset_name: EnumProperty(items=get_asset_name_items, get=get_asset_name, set=set_asset_name)

    def get_selected_asset(self):
        global _selected_asset
        global loading_asset
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

    selected_asset = property(get_selected_asset)

    def get_asset_quality_items(self, context):
        items = []
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


def register():
    bpy.types.Scene.asset_bridge = PointerProperty(type=AssetBridgeSettings)


def unregister():
    del bpy.types.Scene.asset_bridge
