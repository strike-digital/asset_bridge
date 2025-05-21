from time import perf_counter

from bpy.types import Property, PropertyGroup

from ..vendor import requests
from .process import format_traceback


def copy_bl_properties(from_data_block: PropertyGroup, to_data_block: PropertyGroup, print_errors=False):
    """Copy all of the blender properties from one property group to another."""
    for prop in from_data_block.bl_rna.properties:
        if isinstance(prop, Property):
            try:
                setattr(to_data_block, prop.identifier, getattr(from_data_block, prop.identifier))
            except AttributeError as e:
                if print_errors:
                    print(prop, e)


# def check_internet(host="8.8.8.8", port=53, timeout=3):
#     """
#     Check whether the user has an active internet connection
#     taken from: https://stackoverflow.com/a/33117579/18864758

#     Host: 8.8.8.8 (google-public-dns-a.google.com)
#     OpenPort: 53/tcp
#     Service: domain (DNS/TCP)
#     """
#     try:
#         socket.setdefaulttimeout(timeout)
#         socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
#         return True
#     except socket.error as ex:
#         print(ex)
#         return False

# import urllib3

# def check_interneet():
#     start = perf_counter()
#     http = urllib3.PoolManager(timeout=3.0)
#     r = http.request('GET', 'google.com', preload_content=False)
#     code = r.status
#     r.release_conn()
#     if code == 200:
#         print(f"{perf_counter() - start:.5f}")
#         return True
#     else:
#         return False

# def check_internet(timeout=.3) -> bool:
#     """
#     Check whether the user has an active internet connection
#     taken from: https://stackoverflow.com/a/29854274/18864758

#     Host: 8.8.8.8 (google-public-dns-a.google.com)
#     Service: domain (DNS/TCP)
#     """
#     # return True
#     conn = http.client.HTTPSConnection("8.8.8.8", timeout=timeout)
#     try:
#         conn.request("HEAD", "/")
#         return True
#     except Exception as e:
#         print(e)
#         return False
#     finally:
#         conn.close()


def check_internet(url="http://www.google.com/", timeout=5):
    """ "
    Check whether the user has an active internet connection
    taken from: https://stackoverflow.com/a/33117579/18864758
    """
    start = perf_counter()
    try:
        _ = requests.head(url, timeout=timeout)
        return True
        print(f"{perf_counter() - start:.5f}")
    except (requests.ConnectionError, requests.ReadTimeout) as e:
        print(format_traceback(e))
        return False
        print("No internet connection available.")
    return False
