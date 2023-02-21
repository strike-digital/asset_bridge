from bpy.types import Property, PropertyGroup


def copy_bl_settings(from_data_block: PropertyGroup, to_data_block: PropertyGroup, print_errors=False):
    """Copy all of the blender properties from one property group to another."""
    for prop in from_data_block.bl_rna.properties:
        if isinstance(prop, Property):
            try:
                setattr(to_data_block, prop.identifier, getattr(from_data_block, prop.identifier))
            except AttributeError as e:
                if print_errors:
                    print(prop, e)
