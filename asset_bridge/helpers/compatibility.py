

from bpy.types import AssetMetaData, Context, FileSelectEntry
from ..constants import IS_4_0


def get_active_asset(context: Context) -> FileSelectEntry | None:
    """
    Needed for 4.0 compatibility.
    Get the currently active asset in the asset browser.
    """
    return context.asset if IS_4_0 else context.asset_file_handle


def get_asset_metadata(asset_handle: FileSelectEntry) -> AssetMetaData:
    """
    Needed for 4.0 compatibility.
    Get the metadata for the given asset representation.
    """
    return asset_handle.metadata if IS_4_0 else asset_handle.asset_data


def get_active_asset_library_name(context: Context) -> str:
    """
    Needed for 4.0 compatibility.
    Get the name of the currently active asset library
    """
    params = context.area.spaces.active.params
    return params.asset_library_reference if IS_4_0 else params.asset_library_ref