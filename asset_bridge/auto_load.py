import sys
import bpy
import typing
import inspect
import pkgutil
import importlib
from pathlib import Path

__all__ = (
    "init",
    "register",
    "unregister",
)
manual_modules = []

modules = None
ordered_classes = None


def init():
    global modules
    global ordered_classes

    modules = get_all_submodules(Path(__file__).parent)
    ordered_classes = get_ordered_classes_to_register(modules)
    ordered_classes.sort(key=lambda cls: cls.__reg_order__ if hasattr(cls, "__reg_order__") else 10000)


def register():
    global modules
    global ordered_classes

    # Custom attributes to prevent registering, and to enable proper registration order
    for cls in ordered_classes.copy():
        mod = sys.modules[cls.__module__]
        if (hasattr(cls, "__no_reg__") and cls.__no_reg__) or (hasattr(mod, "__no_reg__") and mod.__no_reg__):
            ordered_classes.remove(cls)

    for module in manual_modules:
        if hasattr(module, "register"):
            print(module.__name__)
            module.register()

    for cls in ordered_classes:
        bpy.utils.register_class(cls)

    for module in modules.copy():
        if module.__name__ == __name__ or module in manual_modules or\
                hasattr(module, "__no_reg__") and module.__no_reg__:
            modules.remove(module)
            continue
        if hasattr(module, "register"):
            module.register()


def unregister():
    for cls in reversed(ordered_classes):
        bpy.utils.unregister_class(cls)

    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "unregister"):
            module.unregister()


# Import modules
#################################################


def get_all_submodules(directory):
    return list(iter_submodules(directory, directory.name))


def iter_submodules(path, package_name):
    for name in sorted(iter_submodule_names(path)):
        yield importlib.import_module("." + name, package_name)


def iter_submodule_names(path, root=""):
    for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
        if is_package:
            sub_path = path / module_name
            sub_root = root + module_name + "."
            yield from iter_submodule_names(sub_path, sub_root)
        else:
            yield root + module_name


# Find classes to register
#################################################


def get_ordered_classes_to_register(modules):
    return toposort(get_register_deps_dict(modules))


def get_register_deps_dict(modules):
    deps_dict = {}
    classes_to_register = set(iter_classes_to_register(modules))
    for cls in classes_to_register:
        deps_dict[cls] = set(iter_own_register_deps(cls, classes_to_register))
    return deps_dict


def iter_own_register_deps(cls, own_classes):
    yield from (dep for dep in iter_register_deps(cls) if dep in own_classes)


def iter_register_deps(cls):
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            yield dependency


def get_dependency_from_annotation(value):
    if isinstance(value, tuple) and len(value) == 2:
        if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
            return value[1]["type"]
    return None


def iter_classes_to_register(modules):
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        if any(base in base_types for base in cls.__bases__):
            if not getattr(cls, "is_registered", False):
                yield cls


def get_classes_in_modules(modules):
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes


def iter_classes_in_module(module):
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value


def get_register_base_types():
    return set(
        getattr(bpy.types, name) for name in [
            "Panel", "Operator", "PropertyGroup", "AddonPreferences", "Header", "Menu", "Node", "NodeSocket",
            "NodeTree", "UIList", "RenderEngine"
        ])


# Find order to register to solve dependencies
#################################################


def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value: deps_dict[value] - sorted_values for value in unsorted}
    return sorted_list