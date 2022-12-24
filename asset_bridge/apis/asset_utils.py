import json
from ..constants import DIRS
from ..api import apis
from .asset_types import AssetAPI


def register_api(api: AssetAPI):
    """Takes an asset api and initialises all of the asset lists with either cached or new data."""
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

    # Write the new cached data
    with open(api_file, "w") as f:
        json.dump(asset_lists_dict, f, indent=2)
