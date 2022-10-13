import os
from pathlib import Path
from threading import Thread

import bpy
import gpu
from bpy.types import Operator
from gpu_extras.batch import batch_for_shader
from bpy.props import BoolProperty, StringProperty, FloatVectorProperty
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_origin_3d, location_3d_to_region_2d
from mathutils import Vector as V

from .vendor import requests
from .constants import DIRS
from .helpers import Op, Progress, ensure_asset_library, vec_lerp
from .assets import Asset, asset_list


@Op("asset_bridge", undo=False)
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

    location: FloatVectorProperty(description="The location to put the imported asset/where to draw the progress")

    at_mouse: BoolProperty(
        description="Whether to import the asset at the point underneath the mouse cursor, or instead at the 3d cursor")

    link: BoolProperty(
        description="Whether to link the asset from the downloaded file, or to append it fully into the scene")

    from_asset_browser: BoolProperty(description="Whether the asset is being imported from the asset browser or not")

    # Operators can't have material slots as properties, so this needs to be set at a class level
    # when the operator is called
    material_slot = None

    def get_active_region(self, mouse_pos, context):
        """Get the window region of the area the under the mouse position"""
        mouse_pos = V(mouse_pos)
        for area in context.screen.areas:
            if (area.x < mouse_pos.x < area.x + area.width) and (area.y < mouse_pos.y < area.y + area.height):
                for region in area.regions:
                    if region.type == "WINDOW":
                        return region
        else:
            return None

    def invoke(self, context, event):
        self.mouse_pos_region = V((event.mouse_region_x, event.mouse_region_y))
        self.mouse_pos_window = V((event.mouse_x, event.mouse_y))
        return self.execute(context)

    def execute(self, context):

        if self.at_mouse:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            if context.region:
                region = context.region
                coord = self.mouse_pos_region
            else:
                region = self.get_active_region(self.mouse_pos_window, context)
                coord = self.mouse_pos_window - V((region.x, region.y))
            r3d = region.data

            view_vector = V(region_2d_to_vector_3d(region, r3d, coord))
            ray_origin = V(region_2d_to_origin_3d(region, r3d, coord))

            location = context.scene.ray_cast(depsgraph, ray_origin, view_vector)[1]

            if location == V((0., 0., 0.)):
                # If the ray doesn't intersect with any mesh, place it on the xy plane
                # If view vector intersects with ground behind the camera, just place it in front of the camera
                if (view_vector.z > 0 and ray_origin.z > 0) or (view_vector.z < 0 and ray_origin.z < 0):
                    location = ray_origin + view_vector * (ray_origin.length / 2)
                else:
                    # find the intersection with the ground plane
                    p1 = ray_origin
                    p2 = p1 + view_vector

                    x_slope = (p2.x - p1.x) / (p2.z - p1.z)
                    y_slope = (p2.y - p1.y) / (p2.z - p1.z)
                    xco = p1.x - (x_slope * p1.z)
                    yco = p1.y - (y_slope * p1.z)

                    location = V((xco, yco, 0.))
        else:
            location = self.location or context.scene.cursor.location

        ab = context.scene.asset_bridge
        ab = ab.browser if self.from_asset_browser else ab.panel
        ab.import_progress = 0
        asset = Asset(self.asset_name or ab.asset_name)
        quality = self.asset_quality or ab.asset_quality
        material_slot = self.material_slot
        Progress.data = ab
        Progress.propname = "import_progress"
        thread = Thread(
            target=asset.import_asset,
            args=(context, self.link, quality, self.reload),
            kwargs={
                "location": location,
                "material_slot": material_slot
            },
        )

        thread.start()

        if not asset.get_file_path(quality).exists() or self.reload:
            bpy.ops.asset_bridge.draw_progress(
                "INVOKE_DEFAULT",
                location=location,
                from_asset_browser=self.from_asset_browser,
            )

        for area in context.screen.areas:
            for region in area.regions:
                region.tag_redraw()

        self.__class__.material_slot = None
        print("Importing:", asset.label)
        return {'FINISHED'}


_handler = None


@Op("asset_bridge")
class AB_OT_draw_progress(bpy.types.Operator):

    @classmethod
    def poll(cls, context):
        return True

    from_asset_browser: BoolProperty()

    location: FloatVectorProperty()

    def invoke(self, context, event):
        global _handler
        print(event.mouse_x)

        # self.shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        self.done = False
        self.shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        self.image_shader = gpu.shader.from_builtin('2D_IMAGE')
        ab = context.scene.asset_bridge
        ab = ab.browser if self.from_asset_browser else ab.panel
        _handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback_px,
            (context, ab, V(self.location)),
            "WINDOW",
            # "POST_VIEW",
            "POST_PIXEL",
        )
        self._handler = _handler
        self.image = bpy.data.images.load(str(ab.selected_asset.preview_file))
        self.image.name = "hoho"
        self.aspect = self.image.size[0] / self.image.size[1]
        self.texture = gpu.texture.from_image(self.image)
        # context.area.tag_redraw()
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self.done:
            return {"FINISHED"}

        # if event.type in {"RIGHTMOUSE", "ESC"} and not event.shift:
        #     return self.cancelled()

        return {"PASS_THROUGH"}

    def finish(self):
        print("Done")
        self.done = True
        global _handler
        _handler = None
        # bpy.data.images.remove(self.image)
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, "WINDOW")
        return {"FINISHED"}

    def cancelled(self):
        self.finish()
        return {"CANCELLED"}

    def draw_callback_px(self, context, ab, location):
        if not ab.import_progress_active:
            self.finish()

        coords = (
            (0, 0),
            (0, 1),
            (1, 1),
            (1, 0),
        )

        indices = (
            (0, 1, 2),
            (2, 3, 0),
        )

        line_indeces = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
        ]

        fac = ab.import_progress / 100
        offset = location_3d_to_region_2d(context.region, context.region.data, location)
        size = V([100] * 2)
        size.x *= self.aspect
        line_width = 2

        # Arrow
        height = .16
        arrow_coords = [V(c) * size + offset - V((line_width / 2, 0)) for c in [(0, 0), (0, height), (height, height)]]
        # arrow_coords = [c - V((0, height * size.y)) for c in arrow_coords]
        offset.y += height * size.y
        # height *= size.y

        # Lines
        bar_height = 20
        line_coords = [V(c) * size + V((0, bar_height if c[1] else 0)) for c in coords]
        line_coords = [c + offset for c in line_coords]
        line_coords += [line_coords[0] + V((0, bar_height)), line_coords[3] + V((0, bar_height))]
        line_indeces += [[4, 5]]

        # Image
        image_offset = offset.copy()
        image_offset.y += bar_height
        image_coords = tuple(V(c) * size + image_offset for c in coords)

        # Loading bar
        size.y = bar_height
        size.x *= fac
        bar_coords = tuple(V(c) * size + offset for c in coords)

        gpu.state.blend_set("ALPHA")
        sh = self.shader
        # Image
        batch = batch_for_shader(self.image_shader, 'TRIS', {"pos": image_coords, "texCoord": coords}, indices=indices)
        self.image_shader.uniform_sampler("image", self.texture)
        self.image_shader.bind()
        batch.draw(self.image_shader)

        # Colour
        batch = batch_for_shader(sh, 'TRIS', {"pos": bar_coords}, indices=indices)
        sh.bind()
        alpha = 1
        color = vec_lerp(fac, (1, 0, 0, alpha), (0, .8, 0, alpha))
        sh.uniform_float("color", color)
        batch.draw(sh)

        # Lines
        gpu.state.line_width_set(2)
        batch = batch_for_shader(sh, 'LINES', {"pos": line_coords}, indices=line_indeces)
        sh.bind()
        line_colour = (1, 1, 1, .9)
        sh.uniform_float("color", line_colour)
        batch.draw(sh)

        # Arrow
        batch = batch_for_shader(sh, 'TRIS', {"pos": arrow_coords})
        sh.bind()
        alpha = 1
        sh.uniform_float("color", line_colour)
        batch.draw(sh)


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
        setattr(context.scene.asset_bridge.panel, self.prop_name, value)
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
        Progress.data = context.scene.asset_bridge.panel
        Progress.propname = "preview_download_progress"
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

    region: BoolProperty()

    def invoke(self, context, event):
        ab = context.scene.asset_bridge
        if self.region:
            ab.mouse_pos = event.mouse_region_x, event.mouse_region_y
        else:
            ab.mouse_pos = event.mouse_x, event.mouse_y
        print(list(ab.mouse_pos))
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


def unregister():
    if _handler:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, "WINDOW")