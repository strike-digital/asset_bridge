from bpy.types import Context, AddonPreferences


def get_prefs(context: Context) -> AddonPreferences:
    return context.preferences.addons[__package__.split(".")[0]].preferences
