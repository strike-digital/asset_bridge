from collections import OrderedDict
from ..asset_utils import register_api
from ..asset_types import AssetAPI
from .ph_asset_list import PH_AssetList


class PolyHavenAPI(AssetAPI):

    name = "poly_haven"
    url = "http://polyhaven.com"
    description = """Poly Haven is a curated public asset library for visual effects artists and game designers,
    providing useful high quality 3D assets in an easily obtainable manner.""".replace("\n    ", "")
    asset_lists = OrderedDict({
        "PolyHavenAssets": PH_AssetList,
    })


register_api(PolyHavenAPI)