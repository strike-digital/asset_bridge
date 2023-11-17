from ..operators.op_open_folder import AB_OT_open_folder
from ..operators.op_create_ab_collection import AB_OT_create_ab_collection
from bpy.types import Context, Panel, UILayout
from bpy_extras.asset_utils import AssetBrowserPanel
from ..helpers.prefs import get_prefs

from ..settings import get_ab_scene_settings, get_ab_settings
from ..constants import AB_COLLECTION_NAME, DIRS, ASSET_LIB_NAME
from .ui_helpers import draw_inline_prop, draw_left_aligned_prop, draw_section_header, wrap_text
from ..helpers.btypes import BPanel


@BPanel(space_type="FILE_BROWSER", region_type="TOOLS", label="Asset Info")
class AB_PT_asset_info(Panel, AssetBrowserPanel):
    # __no_reg__ = True
    __reg_order__ = 0

    @classmethod
    def poll(cls, context):
        if context.area.ui_type != "ASSETS":
            return False
        if not context.asset:
            return False
        # In 3.5 the assets can also be viewed in th "All" asset library
        if ASSET_LIB_NAME != context.area.spaces.active.params.asset_library_reference:
            ab = get_ab_settings(context)
            try:
                asset = ab.selected_asset
            except KeyError:
                asset = None

            if not asset:
                return False
        return cls.asset_browser_panel_poll(context)

    def draw_import_settings(self, layout: UILayout, context: Context):
        col = layout.column(align=True)
        box = col.box()
        row = box.row(align=True)
        prefs = get_prefs(context)
        ab = get_ab_settings(context)
        ab_scene = get_ab_scene_settings(context)

        # Draw a left aligned open button
        show_settings = prefs.show_import_settings
        subrow = row.row(align=True)
        subrow.alignment = "LEFT"
        subrow.prop(
            prefs,
            "show_import_settings",
            emboss=False,
            text="Import settings",
            icon="DOWNARROW_HLT" if show_settings else "RIGHTARROW_THIN",
        )
        subrow = row.row(align=True)
        subrow.prop(prefs, "show_import_settings", emboss=False, text=" ", icon="NONE", toggle=True)

        subrow = subrow.row(align=True)
        subrow.active = False
        subrow.prop(prefs, "draw_import_settings_at_top", emboss=False, icon="GRIP", text="")
        show = ab.ui_show

        if show_settings:
            box = col.box().column(align=True)
            icon = "DOWNARROW_HLT" if show.import_mat else "RIGHTARROW_THIN"
            draw_section_header(box, "Materials", show, "import_mat", centered=False, icon=icon)
            if show.import_mat:
                col = box.box().column(align=True)
                draw_inline_prop(col, ab_scene, "apply_real_world_scale", "Use real world scale", "", factor=0.9)

            box.separator()

            icon = "DOWNARROW_HLT" if show.import_model else "RIGHTARROW_THIN"
            draw_section_header(box, "Models", show, "import_model", centered=False, icon=icon)
            if show.import_model:
                col = box.box().column(align=True)
                row = draw_inline_prop(
                    col,
                    ab_scene,
                    "import_collection",
                    "Import collection",
                    "",
                    factor=0.5,
                    row=True,
                )
                collection = ab_scene.import_collection
                if not collection or collection.name != AB_COLLECTION_NAME:
                    AB_OT_create_ab_collection.draw_button(row, text="", icon="COLLECTION_NEW")

    def draw(self, context):
        layout = self.layout

        prefs = get_prefs(context)
        if prefs.draw_import_settings_at_top:
            self.draw_import_settings(layout, context)

        # ASSET INFO
        ab = get_ab_settings(context)
        try:
            asset = ab.selected_asset
        except KeyError:
            asset = None

        if not asset:
            if context.area.spaces.active.params.asset_library_reference != ASSET_LIB_NAME:
                return
            box = layout.box()
            box.alert = True
            wrap_text(context, "Asset not found", box, centered=True)
            return

        if message := asset.poll():
            box = layout.box()
            box.separator()
            box.alert = True
            box.scale_y = 0.45
            wrap_text(context, message, box, centered=True)
            box.separator()
            return

        is_downloaded = asset.is_downloaded(ab.asset_quality)

        # Toprow
        col = layout.column(align=True)
        box = col.box()
        bigrow = box.row(align=True)
        row = bigrow.row(align=True)
        if is_downloaded:
            op = AB_OT_open_folder.draw_button(row, text="", icon="FILE_FOLDER", emboss=False)
            op.file_path = str(asset.get_quality_dir(ab.asset_quality))
        else:
            op = AB_OT_open_folder.draw_button(row, text="", icon="IMPORT", emboss=False)
            op.file_path = str(DIRS.assets)

        row = bigrow.row(align=True)
        # row.alignment = "CENTER"
        # text = "   " + asset.label if is_downloaded else asset.label + "    "
        text = "   " + asset.ab_label
        draw_left_aligned_prop(row, prefs, "show_asset_info", text, False)
        if is_downloaded:
            row = bigrow.row(align=True)
            row.alignment = "RIGHT"
            row.prop(ab, "reload_asset", text="", icon="FILE_REFRESH", emboss=ab.reload_asset)

        if prefs.show_asset_info:
            box = col.box()
            box.prop(
                ab,
                "asset_quality",
                text="Quality",
            )

            col = box.column(align=True)
            metadata = asset.ab_metadata
            for item in metadata:
                item.draw(col, context)

        if not prefs.draw_import_settings_at_top:
            self.draw_import_settings(layout, context)
