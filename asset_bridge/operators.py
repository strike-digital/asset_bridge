import os
from pathlib import Path
from threading import Thread

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty

from .vendor import requests
from .constants import DIRS
from .helpers import Op, ensure_asset_library
from .assets import Asset, asset_list


@Op("asset_bridge", undo=True)
class AB_OT_import_asset(Operator):
    """Import the given asset into the current scene"""

    asset_name: StringProperty(
        description="The name of the asset to import. Leave empty to import the currently selected asset",
        default="",
    )

    asset_quality: StringProperty(
        description="The quality of the asset to import. Leave empty to import the currently selected asset quality",
        default="",
    )

    reload: BoolProperty(
        description="Whether to redownload the asset, or to use the local version if it is available.",
        default=False,
    )

    link: BoolProperty(
        description="Whether to link the asset from the downloaded file, or to append it fully into the scene")

    def execute(self, context):
        ab = context.scene.asset_bridge
        asset = Asset(self.asset_name or ab.asset_name)
        quality = self.asset_quality or ab.asset_quality
        thread = Thread(
            target=asset.import_asset,
            args=(context, self.link, quality, self.reload),
            kwargs={"location": context.scene.cursor.location},
        )

        thread.start()
        for area in context.screen.areas:
            for region in area.regions:
                region.tag_redraw()
        print("Importing:", ab.asset_name)
        return {'FINISHED'}


@Op("asset_bridge", undo=True)
class AB_OT_import_model(Operator):
    """Import the given model into the current scene"""

    name: StringProperty()

    def execute(self, context):
        return {"FINISHED"}


@Op("asset_bridge")
class AB_OT_set_prop(Operator):
    """Set a blender property with a specific value"""

    data_path: StringProperty(description="The path to the property's parent")

    prop_name: StringProperty(description="The name of the property to set")

    value: StringProperty(description="The value to set the property to")

    eval_value: BoolProperty(default=True, description="Whether to evaluate the value, or keep it as a string")

    def execute(self, context):
        # I know people hate eval(), but is it really dangerous here?
        # if you downloaded this addon then it's already executing arbitrary code.
        value = eval(self.value) if self.eval_value else self.value
        setattr(eval(self.data_path), self.prop_name, value)
        return {'FINISHED'}


@Op("asset_bridge")
class AB_OT_set_ab_prop(Operator):
    """Set an asset bridge property with a specific value"""

    prop_name: StringProperty(description="The name of the property to set")

    value: StringProperty(description="The value to set the property to")

    eval_value: BoolProperty(default=False, description="Whether to evaluate the value, or keep it as a string")

    message: StringProperty(description="A message to report once the property has been changed")

    def execute(self, context):
        # I know people hate eval(), but is it really dangerous here?
        # if you downloaded this addon then it's already executing arbitrary code.
        value = eval(self.value) if self.eval_value else self.value
        setattr(context.scene.asset_bridge, self.prop_name, value)
        if self.message:
            self.report({"INFO"}, self.message)
        return {'FINISHED'}


@Op("asset_bridge")
class AB_OT_clear_asset_folder(Operator):
    """Remove all downloaded assets"""

    def invoke(self, context, event):
        self.files = 0
        for _, _, files in os.walk(DIRS.library):
            self.files += len(files)

        if self.files:
            return context.window_manager.invoke_props_dialog(self)
        else:
            self.report({"WARNING"}, "There are no asset files to delete")
            return {'FINISHED'}

        # print(context.window_manager.invoke_props_dialog(self))

    def draw_line(self, layout, text):
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text=text)

    def draw(self, context):
        layout = self.layout.column(align=True)
        layout.scale_y = .75
        layout.alert = True
        self.draw_line(layout, "Warning:")
        layout.separator()
        self.draw_line(layout, f"You are about to delete {self.files} asset files")
        self.draw_line(layout, "This cannot be undone")
        layout.separator()

    def execute(self, context):
        downloads = DIRS.library
        for dirpath, dirnames, file_names in os.walk(downloads):
            if Path(dirpath) not in DIRS.all_dirs:
                continue
            for file in file_names:
                if not os.path.isdir(file):
                    os.remove(os.path.join(dirpath, file))
        self.report({"INFO"}, f"Successfully deleted {self.files} asset files")
        return {'FINISHED'}


@Op("asset_bridge", register=False)
class AB_OT_none(Operator):
    """Do nothing :). Useful for some UI stuff"""

    def execute(self, context):
        return {"FINISHED"}


@Op("asset_bridge")
class AB_OT_report_message(Operator):

    severity: StringProperty(default="INFO")

    message: StringProperty(default="")

    def invoke(self, context, event):
        """The report needs to be done in the modal function otherwise it wont show at the bottom of the screen.
        For some reason ¯\_(ツ)_/¯"""  # noqa
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        self.report({self.severity}, self.message)
        return {"FINISHED"}


@Op("asset_bridge")
class AB_OT_download_asset_previews(Operator):

    def execute(self, context):
        asset_list.update()
        ensure_asset_library()
        thread = Thread(target=asset_list.download_all_previews, args=[False])
        thread.start()
        
        # asset_list.download_all_previews(reload=False)

        # ensure_asset_library()

        return {'FINISHED'}


@Op("asset_bridge")
class AB_OT_set_category(Operator):

    category_name: StringProperty()

    def execute(self, context):

        return {'FINISHED'}


@Op("asset_bridge")
class AB_OT_get_mouse_pos(Operator):

    category_name: StringProperty()

    def invoke(self, context, event):
        ab = context.scene.asset_bridge
        ab.mouse_pos = event.mouse_region_x, event.mouse_region_y
        return {'FINISHED'}


@Op("asset_bridge")
class AB_OT_open_author_website(Operator):
    """Open the website of the given author"""

    author_name: StringProperty()

    def execute(self, context):
        data = requests.get(f"https://api.polyhaven.com/author/{self.author_name}").json()
        if "link" in data:
            link = data["link"]
        elif "email" in data:
            link = "mailto:" + data["email"]
        else:
            self.report({"WARNING"}, "No website found for this author")
            return {'FINISHED'}
        bpy.ops.wm.url_open(url=link)
        return {'FINISHED'}
