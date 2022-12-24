import bpy
from queue import Queue


# It's a bad idea to modify blend data in arbitrary threads,
# so if those threads want to do so, they can add a function to the queue
# which will then be executed on the main thread based on a timer
main_thread_queue = Queue()


def main_thread_timer():
    """Go through the functions in the queue and execute them.
    This is checked every n seconds, where n is the return value"""
    while not main_thread_queue.empty():
        func, args, kwargs = main_thread_queue.get()
        # print(f"executing function '{func.__name__}' on main thread")
        func(*args, **kwargs)


def run_in_main_thread(function, args, kwargs=None):
    """Run the given function in the main thread when it is next available.
    This is useful because it is usually a bad idea to modify blend data at arbitrary times on separate threads,
    as this can causes weird error messages, and even crashes."""
    if kwargs is None:
        kwargs = {}
    main_thread_queue.put((function, args, kwargs))
    bpy.app.timers.register(main_thread_timer)


def update_prop(data, name, value):
    """Update a single blender property in the main thread"""
    run_in_main_thread(setattr, (data, name, value))


def ui_update_timer(area, area_types, region_types):
    """Update all given areas, in the main thread"""
    if not isinstance(area_types, set):
        area_types = {area_types}
    if not isinstance(region_types, set):
        area_types = {region_types}
    areas = []
    if area:
        areas = [area]
    else:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type not in area_types:
                    continue
                areas.append(area)
    for area in areas:
        for region in area.regions:
            if region.type not in region_types:
                continue
            region.tag_redraw()
    bpy.context.workspace.status_text_set_internal(None)


def force_ui_update(area=None, area_types={"VIEW_3D", "PREFERENCES"}, region_types={"WINDOW", "UI"}):
    """Sometimes calling tag_redraw doesn't work, but doing it in a timer does"""
    run_in_main_thread(ui_update_timer, args=(area, area_types, region_types))
