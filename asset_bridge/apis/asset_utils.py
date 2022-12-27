import json
from ..constants import DIRS
from ..api import apis
from .asset_types import AssetAPI
from ..vendor import requests
import shutil
from pathlib import Path


def register_api(api: AssetAPI):
    """Takes an asset api and initialises all of the asset lists with either cached or new data."""
    api = api()
    apis[api.name] = api

    # Get the cached asset list data if it exists
    api_file = DIRS.asset_lists / (api.name + ".json")
    asset_lists_dict = {}
    if api_file.exists():
        with open(api_file, "r") as f:
            try:
                asset_lists_dict = json.load(f)
            except json.JSONDecodeError:
                pass

    # Initialize the asset lists with either the cached data, or new data from the internet, from the get_data function
    for name, asset_list in api.asset_lists.items():
        try:
            list_data = asset_lists_dict[asset_list.name]

            # TODO: Remove this!!!!!
            #################################
            if True:
                raise KeyError
            #################################

        except KeyError:
            list_data = asset_list.get_data()
            asset_lists_dict[asset_list.name] = list_data

        # Initialize
        api.asset_lists[name] = asset_list(list_data)

    # Ensure that there are no duplicate names in other apis, so that all assets can be accessed by name
    for name, other_api in apis.items():
        if name == api.name:
            continue

        if duplicates := other_api.all_assets.keys() & api.all_assets.keys():
            for duplicate in duplicates:
                for asset_list in api.asset_lists.values():
                    if duplicate in asset_list.keys():
                        asset = asset_list[duplicate]
                        del asset_list[duplicate]
                        asset_list[duplicate + "_1"] = asset
                        asset.idname = duplicate + "_1"

    # Write the new cached data
    with open(api_file, "w") as f:
        json.dump(asset_lists_dict, f, indent=2)


def file_name_from_url(url: str) -> str:
    return url.split('/')[-1].split("?")[0]


def download_file(url: str, download_path: Path, file_name: str = ""):
    """Download a file from the provided url to the given file path"""
    if not isinstance(download_path, Path):
        download_path = Path(download_path)

    download_path.mkdir(exist_ok=True)
    file_name = file_name or file_name_from_url(url)
    download_path = download_path / file_name

    result = requests.get(url, stream=True)
    if result.status_code != 200:
        with open(DIRS.addon / "log.txt", "w") as f:
            f.write(url)
            f.write(result.status_code)
        raise requests.ConnectionError()

    with open(download_path, 'wb') as f:
        shutil.copyfileobj(result.raw, f)
    return download_path