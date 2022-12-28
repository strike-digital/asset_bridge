from ...constants import DIRS

from ..asset_utils import download_file
from ..asset_types import AssetListItem, AssetMetadataItem


class PH_AssetListItem(AssetListItem):

    def __init__(self, name: str, data: dict):
        asset_types = ["hdri", "texture", "model"]
        self.name = name
        self.label = data["name"]
        self.idname = name

        self.type = asset_types[data["type"]]
        self.categories = data["categories"]
        self.tags = data["tags"]
        self.page_url = f"https://polyhaven.com/a/{name}"

        # TODO: Add more and make them context sensitive
        self.metadata = [
            AssetMetadataItem("Link", self.page_url, "wm.url_opn"),
            AssetMetadataItem("Downloads", f"{data['download_count']:,}"),
            AssetMetadataItem("Tags", data["tags"])
        ]

        # TODO: Maybe load the preview here
        pass

    def download_preview(self):
        size = 128
        url = f"https://cdn.polyhaven.com/asset_img/thumbs/{self.name}.png?width={size}&height={size}"
        download_file(url, DIRS.previews, f"{self.idname}.png")
        # try:
        # except ConnectionError as e:
        #     return str(e)
        # return
        # sleep(random() * .0001)