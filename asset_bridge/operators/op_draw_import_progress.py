from .op_report_message import report_message
from ..gpu_drawing.shaders import ASSET_PROGRESS_SHADER
from ..settings import get_ab_settings
from ..helpers.math import Rectangle, vec_lerp
import bpy
from bpy.props import FloatVectorProperty, StringProperty
from bpy.types import Operator
from bpy_extras.view3d_utils import location_3d_to_region_2d
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Color, Vector as V
from ..btypes import BOperator

handlers = []


@BOperator("asset_bridge")
class AB_OT_draw_import_progress(Operator):

    @classmethod
    def poll(cls, context):
        return True

    task_name: StringProperty()

    location: FloatVectorProperty(description="The position to draw the progress in 3D space")

    def invoke(self, context, event):
        global handlers

        self.done = False
        self.shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        self.image_shader = gpu.shader.from_builtin('2D_IMAGE')
        ab = get_ab_settings(context)
        handlers.append(
            bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_px,
                (context, V(self.location)),
                "WINDOW",
                # "POST_VIEW",
                "POST_PIXEL",
            ))
        self.cancel_box = Rectangle()
        self.handler = handlers[-1]
        self.image = bpy.data.images.load(str(ab.selected_asset.preview_file))
        self.image.name = self.task_name
        self.aspect = self.image.size[0] / self.image.size[1]
        self.texture = gpu.texture.from_image(self.image)
        self.region = context.region
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def get_task(self, context):
        """It's best to get a new reference to the task each iteration, as if the tasks list is modified,
        Blender will invalidate all current python references to tasks, which causes errors when importing
        multiple assets at once"""
        return get_ab_settings(context).tasks.get(self.task_name)

    def modal(self, context, event):
        if self.done:
            context.window.cursor_modal_restore()
            return {"FINISHED"}

        # Handle pressing the cancel button
        mouse_pos = V((event.mouse_x, event.mouse_y)) - V((self.region.x, self.region.y))

        over_cancel = False
        if self.region:
            if self.cancel_box.isinside(mouse_pos):
                over_cancel = True
                context.window.cursor_modal_set("HAND")
            else:
                context.window.cursor_modal_restore()

        if over_cancel and event.type == "LEFTMOUSE" and event.value == "PRESS":
            self.get_task(context).progress.cancel()
            report_message("Download cancelled", severity="WARNING")

        return {"PASS_THROUGH"}

    def finish(self):
        self.done = True
        global handlers
        handlers.remove(self.handler)
        bpy.data.images.remove(self.image)
        bpy.types.SpaceView3D.draw_handler_remove(self.handler, "WINDOW")
        return {"FINISHED"}

    def cancelled(self):
        self.finish()
        return {"CANCELLED"}

    def draw_callback_px(self, context, location):
        task = self.get_task(context)

        if task is None or not task.progress or task.progress.cancelled:  # or not task.progress_prop_active:
            self.finish()
            return

        self.region = context.region

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

        uv = coords
        fac = task.progress_prop / 100
        offset = location_3d_to_region_2d(context.region, context.region.data, location)
        size = V([100] * 2)
        # orig_size_x = size.x
        # size.x *= aspect
        line_width = 2

        # Custom shader version
        if False:
            coords = [V(c) * size + offset for c in coords]
            color = Color()
            color.hsv = (.5, 0, 1)
            size *= 5
            print(self.aspect)
            gpu.state.blend_set("ALPHA")
            batch = batch_for_shader(ASSET_PROGRESS_SHADER, "TRIS", {"pos": coords, "uv": uv}, indices=indices)
            ASSET_PROGRESS_SHADER.bind()
            ASSET_PROGRESS_SHADER.uniform_float("color", (*list(color), 1))
            ASSET_PROGRESS_SHADER.uniform_float("aspect", self.aspect)
            ASSET_PROGRESS_SHADER.uniform_sampler("image", self.texture)
            batch.draw(ASSET_PROGRESS_SHADER)
            gpu.state.blend_set("ALPHA")
            return

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
        image_size = size.copy()
        image_size.x *= self.aspect
        if self.aspect > 1:
            image_size *= 1 / self.aspect

        image_offset = offset.copy()
        image_offset.x += (size.x / 2) - (image_size.x / 2)
        image_offset.y += bar_height + ((size.y / 2) - (image_size.y / 2))
        image_offset.y

        image_coords = tuple(V(c) * image_size + image_offset for c in coords)

        # Loading bar
        bar_size = size.copy()
        bar_size.y = bar_height
        bar_size.x *= fac
        # shorten to make space for cancel box
        bar_size.x *= (size.x - bar_height) / max(size.x, .000001)
        bar_coords = tuple(V(c) * bar_size + offset for c in coords)

        # Cancel box
        c_min = V((size.x - bar_height, 0))
        c_max = V((size.x, bar_height))
        self.cancel_box = Rectangle(c_min + offset, c_max + offset)

        # Add dividing line
        line_coords += [c_min.copy() + offset, V((c_min.x, c_max.y)) + offset]
        line_indeces += [[6, 7]]

        # Add the X button
        cancel_coords = []
        cancel_size = .7
        min_offset = c_min + V([bar_height / 2] * 2)
        max_offset = c_max - V([bar_height / 2] * 2)
        c_min = (c_min - min_offset) * cancel_size + min_offset
        c_max = (c_max - max_offset) * cancel_size + max_offset

        cancel_coords += [c_min, c_max, (c_min.x, c_max.y), (c_max.x, c_min.y)]
        cancel_coords = [V(c) + offset for c in cancel_coords]

        # Background
        background_coords = line_coords[:4]
        sh = self.shader
        gpu.state.blend_set("ALPHA")
        batch = batch_for_shader(sh, 'TRIS', {"pos": background_coords}, indices=indices)
        sh.bind()
        color = (*[.1] * 3, .7)
        sh.uniform_float("color", color)
        batch.draw(sh)

        # Image
        batch = batch_for_shader(self.image_shader, 'TRIS', {"pos": image_coords, "texCoord": coords}, indices=indices)
        self.image_shader.uniform_sampler("image", self.texture)
        self.image_shader.bind()
        batch.draw(self.image_shader)

        # Colour
        batch = batch_for_shader(sh, 'TRIS', {"pos": bar_coords}, indices=indices)
        sh.bind()
        alpha = .8
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
        sh.uniform_float("color", line_colour)
        batch.draw(sh)

        # Cancel button
        batch = batch_for_shader(sh, 'LINES', {"pos": cancel_coords})
        sh.bind()
        line_colour = (1, 0, 0, .9)
        sh.uniform_float("color", line_colour)
        batch.draw(sh)


def unregister():
    for handler in handlers:
        bpy.types.SpaceView3D.draw_handler_remove(handler, "WINDOW")