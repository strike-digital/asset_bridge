from ..asset_types import AssetListItem, AssetMetadataItem


class PH_AssetListItem(AssetListItem):

    def __init__(self, name: str, data: dict):
        asset_types = ["hdri", "texture", "model"]
        self.name = name
        self.label = data["name"]

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