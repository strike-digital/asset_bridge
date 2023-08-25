import json
import os
import webbrowser

from ..api import get_asset_lists

from ..helpers.library import human_readable_file_size
from ..constants import DIRS, FILES
from bpy.types import Context
from ..helpers.btypes import BOperator


@BOperator("asset_bridge")
class AB_OT_open_log_file(BOperator.type):
    def execute(self, context: Context):
        output = ""
        indent = "  "

        output += "Asset lists:\n"
        all_asset_lists = get_asset_lists()
        for asset_list in all_asset_lists.values():
            indent = "  "
            output += f"{indent}{asset_list.name}:\n"
            indent = "    "
            is_initialized = all_asset_lists.is_initialized(asset_list.name)
            if is_initialized:
                output += f"{indent}is initialized: {is_initialized}\n"
                output += f"{indent}no. of assets: {len(asset_list.assets)}\n"
            exists = asset_list.data_cache_file.exists()
            output += f"{indent}cache file exists: {exists}"
            if exists:
                output += f"({human_readable_file_size(os.path.getsize(asset_list.data_cache_file))})"
            output += "\n"
        output += "\n"
        indent = "  "

        output += f"No. of assets: {len(all_asset_lists.all_assets)}\n"
        output += f"No. of previews: {len(list(DIRS.previews.glob('*.png')))}\n\n"

        if FILES.lib_info.exists():
            try:
                output += f"library version: {json.loads(FILES.lib_info.read_text())['version']}\n"
            except json.JSONDecodeError as e:
                output += f"Couldn't load library info file: {e}\n"
        else:
            output += "No library info file found.\n"

        if not DIRS.dummy_assets.exists():
            output += f"Dummy assets folder does not exist: {DIRS.dummy_assets}"
            return

        output += "\nAsset Blends:\n"
        for file in DIRS.dummy_assets.glob("*.blend"):
            output += f"{indent}{file.name}: {human_readable_file_size(os.path.getsize(file))}\n"

        output += "\nCatalog info:\n"
        catalog_files = list(DIRS.dummy_assets.glob("*.cats.txt"))
        catalog_files.sort(key=lambda x: x == FILES.asset_catalog)
        for file in catalog_files:
            with open(file, "r") as f:
                catalogs = len([l for l in f if not l.lstrip().startswith("#") and l.lstrip() and "VERSION" not in l])
            if catalogs:
                output += f"{indent}No. of catalogs in {file.stem}: {catalogs}\n"
            else:
                output += f"{indent} No catalogs found in {file.name}:\n"
                with open(file, "r") as f:
                    for line in f:
                        output += indent * 2 + line

        output += "\nAsset Logs:\n"

        for file in DIRS.dummy_assets.glob("*_log.txt"):
            output += indent + file.name + ":\n"
            with open(file, "r") as f:
                for line in f:
                    output += indent * 2 + line

            output += "\n"

        FILES.log.write_text(output)
        webbrowser.open(FILES.log)
