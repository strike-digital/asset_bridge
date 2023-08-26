import bpy
import gpu
from gpu.types import GPUBatch
from mathutils import Vector as V
from gpu_extras.batch import batch_for_shader

from ..settings import get_ab_settings
from ..constants import DIRS
from ..helpers.math import vec_divide
from ..helpers.btypes import BOperator
from ..helpers.drawing import Shaders, get_active_window_region
from ..apis.asset_utils import download_file, file_name_from_url

handlers = []


@BOperator("asset_bridge")
class AB_OT_view_high_res_previews(BOperator.type):
    """Show a high resolution preview for this asset"""

    def invoke(self, context, event):
        self.event = event
        self.region_size = V((context.region.width, context.region.height))
        self.index = 0

        ab = get_ab_settings(context)
        list_item = ab.selected_asset
        urls = list_item.get_high_res_urls()
        files = []
        for i, url in enumerate(urls):
            fname = f"{list_item.ab_idname}_{i}_{file_name_from_url(url)}"
            file = DIRS.high_res_previews / fname
            if file.exists():
                files.append(file)
                continue
            files.append(download_file(url, DIRS.high_res_previews, file_name=fname))

        self.multiple_images = len(files) > 1

        self.images = []
        self.textures = []
        for file in files:
            image = bpy.data.images.load(str(file))
            image.name = "." + image.name
            image.colorspace_settings.name = "Linear" if bpy.app.version < (4, 0, 0) else "Linear Rec.709"
            self.images.append(image)
            self.textures.append(gpu.texture.from_image(image))

        self.shader = Shaders.UNIFORM_COLOR
        self.image_shader = Shaders.IMAGE

        self._handle = bpy.types.SpaceFileBrowser.draw_handler_add(
            self.draw_callback_px,
            (context, files),
            "WINDOW",
            "POST_PIXEL",
        )
        handlers.append(self._handle)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        self.event = event
        mouse_region = V((event.mouse_region_x, event.mouse_region_y))
        context.window.cursor_modal_set("DEFAULT")

        region = get_active_window_region(V((self.event.mouse_x, self.event.mouse_y)))
        if region:
            self.region_size = V((region.width, region.height))

        if any(c < 0 for c in mouse_region) or any(c > r for (c, r) in zip(mouse_region, self.region_size)):
            if mouse_region != V((-1, -1)):
                return {"PASS_THROUGH"}

        if event.type in {"SPACE"}:
            return {"PASS_THROUGH"}

        if mouse_region.y < 50 and self.multiple_images:
            context.window.cursor_modal_set("HAND")
            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                if mouse_region.x < region.width / 2:
                    self.index -= 1
                else:
                    self.index += 1
                region.tag_redraw()

        if event.type in {"RIGHTMOUSE", "ESC"}:
            return self.cancelled()

        return {"RUNNING_MODAL"}

    def finish(self):
        bpy.types.SpaceFileBrowser.draw_handler_remove(self._handle, "WINDOW")
        bpy.context.window.cursor_modal_restore()
        for image in self.images:
            bpy.data.images.remove(image)
        handlers.remove(self._handle)
        return {"FINISHED"}

    def cancelled(self):
        self.finish()
        return {"CANCELLED"}

    def draw_callback_px(self, context, files):
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
        region_size = self.region_size
        coords = [V(c) for c in coords]
        back_coords = [c * region_size for c in coords]

        sh = self.shader
        gpu.state.blend_set("ALPHA")
        batch: GPUBatch = batch_for_shader(sh, "TRIS", {"pos": back_coords}, indices=indices)
        sh.bind()
        color = (*[0.1] * 3, 0.7)
        sh.uniform_float("color", color)
        batch.draw(sh)

        idx = self.index % len(self.images)
        image = self.images[idx]
        texture = self.textures[idx]

        size = V((image.size[0], image.size[1]))

        coefficient = min(vec_divide(region_size, size))
        size = size * coefficient * 0.9

        offset = (region_size - size) / 2
        image_coords = [c * size + offset for c in coords]
        batch = batch_for_shader(
            self.image_shader,
            "TRIS",
            {"pos": image_coords, "texCoord": coords},
            indices=indices,
        )
        self.image_shader.uniform_sampler("image", texture)
        self.image_shader.bind()
        batch.draw(self.image_shader)

        if not self.multiple_images:
            return

        # Arrows
        arrow_coords = [
            (1.5, 0),
            (1.5, 2),
            (0, 1),
        ]
        arrow_coords = [V(c) for c in arrow_coords]
        size = V([25] * 2)
        color = (*[1] * 3, 0.7)

        offset = V((0, 0))
        offset.x = (region_size.x - (size.x * 1.5)) / 2 - size.x
        offset.y += 10
        coords = [c * size + offset for c in arrow_coords]
        batch: GPUBatch = batch_for_shader(sh, "TRIS", {"pos": coords})
        sh.bind()
        sh.uniform_float("color", color)
        batch.draw(sh)

        offset = V((0, 0))
        offset.x = (region_size.x - (size.x * 1.5)) / 2 + size.x
        offset.y += 10
        for coord in arrow_coords:
            coord.x = 1.5 - coord.x
        coords = [c * size + offset for c in arrow_coords]
        batch: GPUBatch = batch_for_shader(sh, "TRIS", {"pos": coords})
        sh.bind()
        sh.uniform_float("color", color)
        batch.draw(sh)


def unregister():
    for handler in handlers:
        bpy.types.SpaceFileBrowser.draw_handler_remove(handler, "WINDOW")
