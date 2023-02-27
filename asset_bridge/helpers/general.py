import socket

from bpy.types import Property, PropertyGroup


def copy_bl_properties(from_data_block: PropertyGroup, to_data_block: PropertyGroup, print_errors=False):
    """Copy all of the blender properties from one property group to another."""
    for prop in from_data_block.bl_rna.properties:
        if isinstance(prop, Property):
            try:
                setattr(to_data_block, prop.identifier, getattr(from_data_block, prop.identifier))
            except AttributeError as e:
                if print_errors:
                    print(prop, e)


def check_internet(host="8.8.8.8", port=53, timeout=3):
    """
    Check whether the user has an active internet connection
    taken from: https://stackoverflow.com/a/33117579/18864758

    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False