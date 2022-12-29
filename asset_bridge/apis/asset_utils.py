import json
from typing import Type
from ..constants import DIRS
from ..api import asset_lists
from .asset_types import AssetList
from ..vendor import requests
import shutil
from pathlib import Path


def register_asset_list(new_list: Type[AssetList]):
    """Takes an asset api and initialises all of the asset lists with either cached or new data."""
    # asset_lists[asset_list.name] = asset_list

    # Get the cached asset list data if it exists
    list_file = DIRS.asset_lists / (new_list.name + ".json")
    asset_list_data = {}
    if list_file.exists():
        with open(list_file, "r") as f:
            try:
                asset_list_data = json.load(f)
            except json.JSONDecodeError:
                pass

    # Initialize the asset lists with either the cached data, or new data from the internet, from the get_data function
    # TODO: Remove this!!!!!
    #################################
    if True or not asset_list_data:
        asset_list_data = new_list.get_data()

    # Ensure that there are no duplicate names in other apis, so that all assets can be accessed by name
    for name, other_list in asset_lists.items():
        if name == new_list.name:
            continue

        if duplicates := other_list.assets.keys() & new_list.assets.keys():
            for duplicate in duplicates:
                asset = new_list[duplicate]
                del new_list[duplicate]
                new_list[duplicate + "_1"] = asset
                asset.idname = duplicate + "_1"

    # Initialize
    asset_lists[new_list.name] = new_list(asset_list_data)

    # Write the new cached data
    with open(list_file, "w") as f:
        json.dump(asset_list_data, f, indent=2)


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