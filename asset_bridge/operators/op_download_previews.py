from collections import deque
import os
import random
from time import perf_counter
from random import choice
from itertools import islice
from threading import Thread

import bpy
from bpy.props import IntProperty, BoolProperty
from bpy.types import Operator

from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..constants import DIRS, PREVIEW_DOWNLOAD_TASK_NAME
from ..helpers.btypes import BOperator
from ..helpers.general import check_internet
from ..apis.asset_types import AssetListItem
from .op_report_message import report_message
from ..helpers.main_thread import run_in_main_thread
from ..vendor.requests.exceptions import ConnectTimeout


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

        if not check_internet():
            report_message("Cannot download the asset previews as there is no internet connection", severity="ERROR")
            return {"CANCELLED"}

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
                try:
                    asset.download_preview()
                except (ConnectionError, ConnectTimeout) as e:
                    report_message(
                        severity="ERROR",
                        message=f"Could not download the preview for {asset.idname}:\n{e}",
                        main_thread=True,
                    )
                progress.increment()
                names.remove(asset.idname)

            def update_message():
                """Update the message with a random preview name.
                (Its mainly aesthetic, but also good for knowing which preview is taking so long)"""
                if not names:
                    return
                # random.
                random.seed(len(assets) / len(list(names)))
                progress.message = f"(1/2) Downloading: {choice(list(names))}.png"
                if not finished:
                    return .01

            bpy.app.timers.register(update_message)

            start = perf_counter()

            # Start 40 threads, each downloading previews from a queue.
            # Not sure if this is an optimal number for all machines, or just mine.
            # TODO: Test on the laptop.
            target_threads = 40

            download_queue = deque(assets.values())

            def download_previews():
                """Continuously download previews until the queue is empty"""
                while download_queue:
                    asset = download_queue.pop()
                    download_preview(asset)

            threads: list[Thread] = []

            # Start the target number of threads
            for _ in range(target_threads):
                thread = Thread(target=download_previews)
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            finished = True
            if progress.cancelled:
                report_message(message="Download cancelled.", main_thread=True)
                task.finish()
                return

            task.finish()
            report_message(
                message=f"Downloaded {len(assets)} asset previews in {perf_counter() - start:.2f}s",
                main_thread=True,
            )

            run_in_main_thread(bpy.ops.asset_bridge.create_dummy_assets)

        # Download the previews on a separate thread to avoid freezing the UI
        thread = Thread(target=download_all_previews)
        thread.start()
        return {"FINISHED"}
