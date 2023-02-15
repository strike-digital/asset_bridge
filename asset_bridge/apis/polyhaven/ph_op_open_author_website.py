import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from ...helpers.btypes import BOperator
from ...vendor import requests


@BOperator("asset_bridge")
class AB_OT_open_ph_author_website(Operator):
    """Open the website of the given author"""

    author_name: StringProperty()

    def execute(self, context):
        data = requests.get(f"https://api.polyhaven.com/author/{self.author_name}").json()
        if "link" in data:
            link = data["link"]
        elif "email" in data:
            link = "mailto:" + data["email"]
        else:
            self.report({"WARNING"}, "No website found for this author")
            return {'FINISHED'}
        bpy.ops.wm.url_open(url=link)
        return {'FINISHED'}