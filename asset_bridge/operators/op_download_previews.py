from itertools import islice
import os
from random import choice
from threading import Thread
from time import perf_counter
from ..helpers.main_thread import run_in_main_thread

import bpy

from .op_report_message import report_message

from ..apis.asset_types import AssetListItem
from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..constants import DIRS, PREVIEW_DOWNLOAD_TASK_NAME
from ..btypes import BOperator
from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty


@BOperator("asset_bridge")
class AB_OT_download_previews(Operator):
    """Download the previews for all of the assets"""

    reload: BoolProperty()

    test_number: IntProperty(
        description="Download a the given number of previews, used for testing without taking tons of time.",
        options={"HIDDEN", "SKIP_SAVE"},
        default=-1,
    )

    def execute(self, context):
        ab = get_ab_settings(context)

        assets = get_asset_lists().all_assets

        if not self.reload:
            previews = {p.replace(".png", "") for p in os.listdir(DIRS.previews)}
            assets = {k: v for k, v in assets.items() if k not in previews}

        if self.test_number != -1:
            # Pick 10 items from the list, rather than downloading all of them
            assets = dict(islice(assets.items(), self.test_number))

        if not assets:
            report_message("No new asset previews to download")
            return {"CANCELLED"}

        task = ab.new_task(name=PREVIEW_DOWNLOAD_TASK_NAME)
        progress = task.new_progress(len(assets))

        def download_all_previews():
            """Download each preview on a separate thread to improve the speed.
            Ideally I could use multiprocessing here as well as Threading, but that doesn't seem to play nicely
            with Blender, and while I'm sure it *could* work, I can't be bothered figuring it out."""
            names = set(assets.keys())
            finished = False

            def download_preview(asset: AssetListItem):
                """Download a single preview and increment the progress"""
                if progress.cancelled:
                    return
                asset.download_preview()
                progress.increment()
                names.remove(asset.idname)

            def update_message():
                """Update the message with a random preview name.
                (Its mainly aesthetic, but also good for knowing which preview is taking so long)"""
                if not names:
                    return
                progress.message = f"(1/2) Downloading: {choice(list(names))}.png"
                if not finished:
                    return .01

            bpy.app.timers.register(update_message)

            start = perf_counter()

            # Start a thread for every preview. This probably not the most efficient,
            # but in my testing it's just as fast as downloading the previews in chunks...
            # I don't know if that also works for lower end hardware though.
            # TODO: Test on the laptop.
            threads: list[Thread] = []
            for asset in assets.values():
                thread = Thread(target=download_preview, args=[asset])
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            finished = True
            if progress.cancelled:
                report_message(message="Download cancelled.", main_thread=True)
                return

            # task.finish()
            report_message(
                message=f"Downloaded {len(assets)} asset previews in {perf_counter() - start:.2f}s",
                main_thread=True,
            )

            run_in_main_thread(bpy.ops.asset_bridge.create_dummy_assets)

        # Download the previews on a separate thread to avoid freezing the UI
        thread = Thread(target=download_all_previews)
        thread.start()
        return {"FINISHED"}
