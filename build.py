import subprocess
from pathlib import Path

from builder.builder import AddBuildSubstitution, AddonBuilder


def main():
    addon_dir = Path(__file__).parent / "asset_bridge"
    builder = AddonBuilder(
        addon_dir,
        "Asset Bridge",
        github_repo="strike-digital/asset_bridge",
    )
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

    build = builder.build(Path(__file__).parent / "builds", file_list=files, update_bl_info=True)

    print(build.check_tag_exists())
    print(build.create_tag())
    print(build.check_tag_exists())
    # build.upload_github_release(release_message="test")

    # webbrowser.open("https://github.com/strike-digital/asset_bridge/releases/new")
    # webbrowser.open("https://blendermarket.com/creator/products/asset-bridge/edit")


if __name__ == "__main__":
    main()
