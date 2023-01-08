from dataclasses import dataclass
from typing import Literal
from bpy.types import Operator, Panel, Menu, Context, UILayout
from bpy.props import StringProperty
import blf
"""A module containing helpers to make defining blender types easier (panels, operators etc.)"""


def wrap_text(self, context: Context, text: str, layout: UILayout, centered: bool = False) -> list[str]:
    """Take a string and draw it over multiple lines so that it is never concatenated."""
    return_text = []
    row_text = ''

    width = context.region.width
    system = context.preferences.system
    ui_scale = system.ui_scale
    width = (4 / (5 * ui_scale)) * width

    dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11, dpi)

    for word in text.split():
        word = f' {word}'
        line_len, _ = blf.dimensions(0, row_text + word)

        if line_len <= (width - 16):
            row_text += word
        else:
            return_text.append(row_text)
            row_text = word

    if row_text:
        return_text.append(row_text)

    for text in return_text:
        row = layout.row()
        if centered:
            row.alignment = "CENTER"
        row.label(text=text)

    return return_text


@dataclass
class BMenu():
    """A decorator for defining blender menus that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the menu class, with whatever arguments you want.
    all of the arguments are optional, as they can all be inferred from the class name and __doc__.
    This works best for menus that use the naming convension ADDON_NAME_MT_menu_name.

    Args:
        label (str): The name of the menu that is displayed when it is drawn in the UI.
        description (str): The description of the menu that is displayed in the tooltip.
        idname (str): a custom identifier for this menu. By default it is the name of the menu class.
    """

    label: str = ""
    description: str = ""
    idname: str = ""

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("PT_")[-1]
        idname = self.idname if self.idname else cls.__name__
        label = self.label or cls_name_end.replace("_", " ").title()

        if self.description:
            panel_description = self.description
        elif cls.__doc__:
            panel_description = cls.__doc__
        else:
            panel_description = label

        class Wrapped(cls, Menu):
            bl_idname = idname
            bl_label = label
            bl_description = panel_description

            wrap_text = wrap_text

            if not hasattr(cls, "draw"):

                def draw(self, context: Context):
                    self.wrap_text(context, "That's a cool menu you've got there", self.layout, centered=True)

        Wrapped.__doc__ = panel_description
        Wrapped.__name__ = cls.__name__
        return Wrapped


@dataclass
class BPanel():
    """A decorator for defining blender Panels that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the panel class, with whatever arguments you want.
    The only required arguments are the space and region types,
    and the rest can be inferred from the class name and __doc__.
    This works best for panels that use the naming convension ADDON_NAME_PT_panel_name.

    Args:
        space_type (str): The type of editor to draw this panel in (e.g. VIEW_3D, NODE_EDITOR, etc.)
        region_type (str): The area of the UI to draw the panel in (almost always UI)
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        label (str): The name of the panel that is displayed in the header (if no header draw function is supplied).
        description (str): The description of the panel that is displayed in the UI.
        idname (str): a custom identifier for this panel. By default it is the name of the panel class.
        parent (str): if provided, this panel will be a subpanel of the given panel bl_idname.
        index (int): if set, this panel will be drawn at that index in the list
            (panels with lower indeces will be drawn higher).
        context (str): The mode to show this panel in. find them here: https://blender.stackexchange.com/a/73154/57981
        popover_width (int): The width of this panel when it is drawn in a popover in UI units (16px x UI scale).
        show_header (bool): Whether to draw the header of this panel.
        default_closed (bool): Whether to draw this panel closed by default before it is opened.
        header_button_expand (bool): Whether to allow buttons drawn in the header to expand to take up the full width,
            or to draw them as squares instead (which is the default).
    """

    space_type: Literal["EMPTY", "VIEW_3D", "NODE_EDITOR", "IMAGE_EDITOR", "SEQUENCE_EDITOR", "CLIP_EDITOR",
                        "DOPESHEET_EDITOR", "GRAPH_EDITOR", "NLA_EDITOR", "TEXT_EDITOR", "CONSOLE", "INFO", "TOPBAR",
                        "STATUSBAR", "OUTLINER", "PROPERTIES", "FILE_BROWSER", "SPREADSHEET", "PREFERENCES",]
    region_type: Literal["UI", "TOOLS", "HEADER", "FOOTER", "TOOL_PROPS", "WINDOW", "CHANNELS", "TEMPORARY", "PREVIEW",
                         "HUD", "NAVIGATION_BAR", "EXECUTE", "TOOL_HEADER", "XR",]
    category: str = ""
    label: str = ""
    description: str = ""
    idname: str = ""
    parent: str = ""
    index: int = -1
    context: str = ""
    popover_width: int = -1
    show_header: bool = True
    default_closed: bool = False
    header_button_expand: bool = False

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("PT_")[-1]
        idname = self.idname if self.idname else cls.__name__
        label = self.label or cls_name_end.replace("_", " ").title()
        label = cls.bl_label if hasattr(cls, "bl_label") else label
        parent_id = self.parent.bl_idname if hasattr(self.parent, "bl_idname") else self.parent

        if self.description:
            panel_description = self.description
        elif cls.__doc__:
            panel_description = cls.__doc__
        else:
            panel_description = label

        options = {
            "DEFAULT_CLOSED": self.default_closed,
            "HIDE_HEADER": not self.show_header,
            "HEADER_BUTTON_EXPAND": self.header_button_expand,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)

        class Wrapped(cls, Panel):
            bl_idname = idname
            bl_label = label
            bl_options = options
            bl_category = self.category
            bl_space_type = self.space_type
            bl_region_type = self.region_type
            bl_description = panel_description

            if self.context:
                bl_context = self.context
            if self.index != -1:
                bl_order = self.index
            if parent_id:
                bl_parent_id = parent_id
            if self.popover_width != -1:
                bl_ui_units_x = self.popover_width

            wrap_text = wrap_text

            # Create a default draw function, useful for quick tests
            if not hasattr(cls, "draw"):

                def draw(self, context: Context):
                    self.wrap_text(context, "That's a cool panel you've got there", self.layout, centered=True)

        Wrapped.__doc__ = panel_description
        Wrapped.__name__ = cls.__name__
        return Wrapped


@dataclass
class BOperator():
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    The only required argument is the category of the operator,
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convension ADDON_NAME_OT_operator_name.

    Args:
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        idname (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        label (str): The name of the operator that is displayed in the UI.
        description (str): The description of the operator that is displayed in the UI.
        dynamic_description (bool): Whether to automatically allow bl_description to be altered from the UI.
        register (bool): Whether to display the operator in the info window and support the redo panel.
        undo (bool): Whether to push an undo step after the operator is executed.
        undo_grouped (bool): Whether to group multiple consecutive executions of the operator into one undo step.
        internal (bool): Whether the operator is only used internally and should not be shown in menu search
            (doesn't affect the operator search accessible when developer extras is enabled).
        wrap_cursor (bool): Whether to wrap the cursor to the other side of the region when it goes outside of it.
        wrap_cursor_x (bool): Only wrap the cursor in the horizontal (x) direction.
        wrap_cursor_y (bool): Only wrap the cursor in the horizontal (y) direction.
        preset (bool): Display a preset button with the operators settings.
        blocking (bool): Block anything else from using the cursor.
        macro (bool): Use to check if an operator is a macro.
        logging (int | bool): Whether to log when this operator is called.
            Default is to use the class logging variable which can be set with set_logging() and is global.
    """

    _logging = False

    @classmethod
    def set_logging(cls, enable):
        """Set the global logging state for all operators"""
        cls._logging = enable

    category: str
    idname: str = ""
    label: str = ""
    description: str = ""
    dynamic_description: bool = True
    invoke: bool = True
    register: bool = True
    undo: bool = False
    undo_grouped: bool = False
    internal: bool = False
    wrap_cursor: bool = False
    wrap_cursor_x: bool = False
    wrap_cursor_y: bool = False
    preset: bool = False
    blocking: bool = False
    macro: bool = False
    # The default is to use the class logging setting, unless this has a value other than -1.
    # ik this is the same name as the module, but I don't care.
    logging: int = -1

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("OT_")[-1]
        idname = f"{self.category}." + (self.idname or cls_name_end)
        label = self.label or cls_name_end.replace("_", " ").title()

        if self.description:
            op_description = self.description
        elif cls.__doc__:
            op_description = cls.__doc__
        else:
            op_description = label

        options = {
            "REGISTER": self.register,
            "UNDO": self.undo,
            "UNDO_GROUPED": self.undo_grouped,
            "GRAB_CURSOR": self.wrap_cursor,
            "GRAB_CURSOR_X": self.wrap_cursor_x,
            "GRAB_CURSOR_Y": self.wrap_cursor_y,
            "BLOCKING": self.blocking,
            "INTERNAL": self.internal,
            "PRESET": self.preset,
            "MACRO": self.macro,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)
        log = self._logging if self.logging == -1 else bool(self.logging)

        class Wrapped(cls, Operator):
            bl_idname = idname
            bl_label = label
            bl_options = options
            __original__ = cls

            wrap_text = wrap_text

            if self.dynamic_description:
                bl_description: StringProperty(default=op_description)

                @classmethod
                def description(cls, context, props):
                    if props:
                        return props.bl_description.replace("  ", "")
                    else:
                        return op_description
            else:
                bl_description = op_description

            if self.invoke:

                def invoke(_self, context, event):
                    """Here we can log whenever an operator using this decorator is invoked"""
                    if log:
                        print(f"Invoke: {idname}")
                    if hasattr(super(), "invoke"):
                        return super().invoke(context, event)
                    else:
                        return _self.execute(context)

        Wrapped.__doc__ = op_description
        Wrapped.__name__ = cls.__name__
        return Wrapped
