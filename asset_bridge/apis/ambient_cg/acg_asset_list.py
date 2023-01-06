from collections import OrderedDict
import csv
from threading import Thread

from ...helpers.math import roundup
from ..asset_utils import register_asset_list

from .acg_asset_list_item import ACG_AssetListItem
from ..asset_types import AssetList
from ...vendor import requests


class ACG_AssetList(AssetList):

    name = "ambient_cg"
    label = "Ambient CG"
    assets: OrderedDict[str, ACG_AssetListItem] = OrderedDict()

    url = "https://ambientcg.com/"
    description = """A massive repository of CC0 assets created by Lennart Demmes""".replace("\n    ", "")

    @staticmethod
    def get_data() -> dict:
        """The Ambient CG api only allows us to get the data for 100 assets at a time,
        so this sends enough requests to cover all of the assets, each in their own thread.
        Idk if this undermines the point of the 100 limit in the first place,
        but it's necessary to get all of the info needed for the addon to work"""

        # All of the parameters that can be passed, the more that are passed, the slower the request
        params = [
            "statisticsData",  # Yes, it is the fastest to get, and also good to be able to see downloads etc.
            "tagData",  # Yes
            # "displayData",  # Maybe, depends if we want to display info on how the asset is created
            "dimensionsData",  # Yes, it hase very little impact on the speed
            # "relationshipData",  # Not needed, it's for getting the SBSAR used to create the material
            # "neighbourData",  # Not needed, gets the id of the previous and next assets in the list
            # "downloadData",  # Not needed, gets various file paths for the file downloads, csv is probably faster
            # "previewData",  # Maybe, used to open the interactive material preview
            # "mapData",  # Probably not, used to get a list of the different maps available, but very little performance cost
            # "usdData",  # No, Just shows whether the asset has Usd available
            # "imageData",  # No, needed to be able to get the previews, but I think I can get them automatically
        ]

        base_url = "https://ambientcg.com/api/v2/full_json"
        url = f"{base_url}?limit=100&include={','.join(params)}"

        # Get total number of assets
        initial_url = f"{base_url}?limit=0"
        total = requests.get(initial_url).json()["numberOfResults"]

        quality_data = {}
        threads: list[Thread] = []

        def get_csv_data():
            csv_url = "https://ambientcg.com/api/v2/downloads_csv"

            with requests.get(csv_url, stream=True) as r:
                lines = (line.decode('utf-8') for line in r.iter_lines())
                first = True
                for row in csv.reader(lines):
                    if first:
                        first = False
                        continue
                    levels = quality_data.get(row[0], {})
                    levels[row[1]] = {"size": int(row[3])}
                    quality_data[row[0]] = levels
        
        thread = Thread(target=get_csv_data)
        thread.start()
        threads.append(thread)

        all_data = {}

        def get_asset_data(offset):
            """Send a request to get the info for 100 assets with the given offset (in number of assets)"""
            page_url = f"{url}&offset={offset}"
            retval = requests.get(page_url).json()
            assets = {a["assetId"]: a for a in retval["foundAssets"]}
            all_data.update(assets)

        # Iterate through the pages and start a new thread with the request
        for offset in range(roundup(total, 100) // 100):
            thread = Thread(target=get_asset_data, args=[offset * 100])
            thread.start()
            threads.append(thread)

        # Wait till all threads have finished
        for thread in threads:
            thread.join()

        for name, data in quality_data.items():
            all_data[name]["quality_levels"] = data

        return all_data

    def __init__(self, data: dict):
        self.assets = OrderedDict()
        # Only load assets that are supported
        # TODO: support more asset types (Terrain, Decals, Images, Atlasses etc.)
        for name, asset_info in data.items():
            if asset_info["dataType"] in {"Material", "HDRI", "3DModel"}:
                self.assets[name] = ACG_AssetListItem(name, asset_info)


register_asset_list(ACG_AssetList)