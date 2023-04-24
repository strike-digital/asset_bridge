from time import time
from .op_cancel_task import cancel_task
from ..helpers.prefs import get_prefs
import bpy
import gpu
import bl_math
from bpy.props import StringProperty, FloatVectorProperty
from bpy.types import Context, Operator
from mathutils import Color
from mathutils import Vector as V
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d

from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..helpers.math import Rectangle, lerp
from ..helpers.btypes import BOperator
from ..helpers.drawing import get_active_window_region
from .op_report_message import report_message
# from ..gpu_drawing.shaders import ASSET_PROGRESS_SHADER

handlers = []


@BOperator("asset_bridge")
class AB_OT_draw_import_progress(Operator):

    @classmethod
    def poll(cls, context):
        return True

    task_name: StringProperty()

    location: FloatVectorProperty(description="The position to draw the progress in 3D space")

    asset_id: StringProperty()

    def invoke(self, context, event):
        global handlers

        self.done = False
        self.shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        self.image_shader = gpu.shader.from_builtin('2D_IMAGE')
        handlers.append(
            bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_px,
                (context, V(self.location)),
                "WINDOW",
                # "POST_VIEW",
                "POST_PIXEL",
            ))
        self.start_time = time()
        self.factor = 0
        self.finish_time = 0

        self.cancel_box = Rectangle()
        self.handler = handlers[-1]
        asset_list_item = get_asset_lists().all_assets[self.asset_id]
        self.image = bpy.data.images.load(str(asset_list_item.preview_file))
        self.image.name = self.task_name
        self.aspect = self.image.size[0] / self.image.size[1]
        self.texture = gpu.texture.from_image(self.image)
        self.region = get_active_window_region(V((event.mouse_x, event.mouse_y)), fallback_area_type="VIEW_3D")
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
            cancel_task(self.task_name)
            # self.get_task(context).cancel()
            report_message("INFO", "Download cancelled")

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

    def draw_callback_px(self, context: Context, location: V):
        task = self.get_task(context)

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

        if task is None or not task.progress or task.cancelled or task.finished:  # or not task.progress_prop_active:
            if not self.finish_time:
                self.finish_time = time()

        # Handle scaling up at the start and down at the end animations
        redraw = False
        prefs = get_prefs(context)
        scale = V((1, 1))
        scale *= prefs.widget_scale * context.preferences.view.ui_scale
        if self.finish_time:
            time_diff = time() - self.finish_time
        else:
            time_diff = time() - self.start_time

        speed = 1000  # Overall animation speed
        popup_time = .4 / prefs.widget_anim_speed / speed
        if time_diff < popup_time:
            time_diff /= popup_time
            time_diff = bl_math.smoothstep(0, popup_time, time_diff)
            time_diff = 1 - time_diff if self.finish_time else time_diff
            scale *= time_diff
            redraw = True
        elif self.finish_time:
            self.finish()
            return

        # Smooth the bar animation
        target = 1 if self.finish_time else task.progress_prop / 100
        fac = lerp(min(.1 * prefs.widget_anim_speed * speed, 1), self.factor, target)
        if (target - fac) > .01:  # Avoid unnecessary updates
            redraw = True
        self.factor = fac

        if redraw:
            bpy.app.timers.register(context.area.tag_redraw, first_interval=.01)

        uv = coords
        offset = location_3d_to_region_2d(context.region, context.region.data, location)

        line_width = 2 * prefs.widget_scale
        size = scale * 100

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
        bar_height = 20 * scale.y
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
        # Hue lerp rather than rgb lerp to get nicer colours
        color = Color()
        color.hsv = (lerp(fac, 0, 1 / 3), 1, lerp(fac, 1, .8))
        color = list(color) + [alpha]
        sh.uniform_float("color", color)
        batch.draw(sh)

        # Lines
        gpu.state.line_width_set(line_width)
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