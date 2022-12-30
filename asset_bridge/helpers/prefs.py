from typing import TYPE_CHECKING
from bpy.types import Context, AddonPreferences as ABAddonPreferences

# Get proper type hinting without causing a circular import loop.
if TYPE_CHECKING:
    from ..preferences import ABAddonPreferences  # noqa F811


def get_prefs(context: Context) -> ABAddonPreferences:
    return context.preferences.addons[__package__.split(".")[0]].preferences
