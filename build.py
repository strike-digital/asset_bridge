import argparse
import subprocess
from getpass import getpass
from pathlib import Path
from threading import Thread

from builder.builder import AddBuildSubstitution, AddonBuild, AddonBuilder

BUILD_DIR = Path(__file__).parent / "builds"
GITHUB_REPO = "strike-digital/asset_bridge"
BM_PRODUCT = "asset-bridge"


def build_addon(version: str):
    addon_dir = Path(__file__).parent / "asset_bridge"
    builder = AddonBuilder(
        addon_dir,
        "Asset Bridge",
        version = tuple(int(part) for part in version.split(".")) if version else None,
        github_repo=GITHUB_REPO,
    )
    if not version:
        builder.set_version_from_github_releases()

    constants_matcher = "__IS_DEV__.*=.*"
    AddBuildSubstitution(
        builder,
        addon_dir / "constants.py",
        matcher=constants_matcher,
        substitution="__IS_DEV__ = False",
        undo=True,
        undo_matcher=constants_matcher,
        undo_substitution="__IS_DEV__ = True",
    )

    # Get file list
    files = [Path(f.decode("utf8")) for f in subprocess.check_output("git ls-files", shell=True).splitlines()]
    files = [addon_dir.parent / f for f in files if "asset_bridge\\" in str(f)]

    cache_dir = addon_dir / "cache"
    files += [f for f in cache_dir.iterdir() if f.suffix == ".json" and f.name not in {"prefs.json"}]

    previews_dir = cache_dir / "previews"
    files += [f for f in previews_dir.iterdir()]

    build = builder.build(BUILD_DIR, file_list=files, update_bl_info=True)
    return build


def get_bm_credentials():
    email = input("Enter Blender Market email: ")
    password = getpass("Enter Blender Market password: ")
    print(f"Got password ({len(password)} chars)")
    return email, password


def upload_github(build: AddonBuild):
    build.upload_github_release()


def upload_bm(build: AddonBuild):
    email, password = get_bm_credentials()
    build.upload_blendermarket_file(email, password)


def get_latest_build() -> AddonBuild:
    files: list[list[tuple, Path]] = []
    for file in BUILD_DIR.iterdir():
        if not file.is_file() or file.suffix != ".zip":
            continue

        parts = file.stem.split("-")
        if len(parts) < 2:
            continue

        try:
            int(parts[1])
        except ValueError:
            print(f"Error with file {file}")
            continue

        version = tuple(int(v) for v in parts[1].split("_"))
        files.append([version, file])

    files.sort(key=lambda x: x[0])
    file = files[-1][1]
    # if files:
    # else:
    # file = BUILD_DIR / f"asset_bridge-{}"

    beta = any(p == "beta" for p in file.stem.split("-"))

    build = AddonBuild(file, version, beta=beta, github_repo=GITHUB_REPO, blendermarket_product=BM_PRODUCT)
    return build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-zip", default=False, action="store_true")
    parser.add_argument("--version", default="")
    parser.add_argument("--upload", choices=["github", "blendermarket", "both"])
    args = parser.parse_args()

    if args.build_zip:
        build = build_addon(args.version)
    else:
        build = get_latest_build()

    build.blendermarket_product = BM_PRODUCT

    if args.upload == "github":
        upload_github(build)

    elif args.upload == "blendermarket":
        upload_bm(build)

    elif args.upload == "both":
        bm_thread = Thread(target=upload_bm, args=[build])
        bm_thread.start()
        gh_thread = Thread(target=upload_github, args=[build])
        gh_thread.start()

        bm_thread.join()
        gh_thread.join()

    # get_bm_credentials()
    # webbrowser.open("https://github.com/strike-digital/asset_bridge/releases/new")
    # webbrowser.open("https://blendermarket.com/creator/products/asset-bridge/edit")


if __name__ == "__main__":
    main()
