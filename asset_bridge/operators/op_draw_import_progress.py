from ..settings import get_ab_settings
from ..helpers.math import vec_lerp
import bpy
from bpy.props import FloatVectorProperty, StringProperty
from bpy.types import Operator
from bpy_extras.view3d_utils import location_3d_to_region_2d
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector as V
from ..btypes import BOperator

handlers = []


@BOperator("asset_bridge")
class AB_OT_draw_import_progress(Operator):

    @classmethod
    def poll(cls, context):
        return True

    task_name: StringProperty()

    location: FloatVectorProperty()

    def invoke(self, context, event):
        global handlers

        self.done = False
        self.shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        self.image_shader = gpu.shader.from_builtin('2D_IMAGE')
        ab = get_ab_settings(context)
        handlers.append(
            bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_px,
                (context, ab, V(self.location), ab.tasks[self.task_name]),
                "WINDOW",
                # "POST_VIEW",
                "POST_PIXEL",
            ))
        self.handler = handlers[-1]
        self.image = bpy.data.images.load(str(ab.selected_asset.preview_file))
        self.image.name = self.task_name
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
        self.done = True
        global handlers
        handlers.remove(self.handler)
        bpy.data.images.remove(self.image)
        bpy.types.SpaceView3D.draw_handler_remove(self.handler, "WINDOW")
        return {"FINISHED"}

    def cancelled(self):
        self.finish()
        return {"CANCELLED"}

    def draw_callback_px(self, context, ab, location, task):
        if not task.progress_prop_active:
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

        fac = task.progress_prop / 100
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


def unregister():
    for handler in handlers:
        bpy.types.SpaceView3D.draw_handler_remove(handler, "WINDOW")