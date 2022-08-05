import requests
import shutil
from pathlib import Path


def download_image(download_path: Path, url):
    res = requests.get(url, stream=True)
    file_name = url.split('/')[-1].split("?")[0]
    download_path = Path(download_path)
    download_path.mkdir(exist_ok=True)
    download_path = str(download_path)
    if download_path and not download_path.endswith("/"):
        download_path += "/"
    path = download_path + file_name
    if res.status_code == 200:
        with open(path,'wb') as f:
            shutil.copyfileobj(res.raw, f)
        print('Image sucessfully Downloaded: ', file_name)
    else:
        print('Image Couldn\'t be retrieved')


headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0"}
# res = requests.get("https://api.polyhaven.com/assets", headers=headers)
# res = requests.get("https://api.polyhaven.com/assets")

# from time import perf_counter
# threads = []
# start = perf_counter()
# for i, asset in enumerate(res.json()):
#     if i > 30:
#         break
#     thread = Thread(target=download_image,
#            args=(Path.cwd() / "images", f"https://cdn.polyhaven.com/asset_img/thumbs/{asset}.png?width=125&height=125"))
#     thread.start()
#     threads.append(thread)
#     # download_image(Path.cwd() / "images", f"https://cdn.polyhaven.com/asset_img/thumbs/{asset}.png?width=125&height=125")

# for thread in threads:
#     thread.join()

# print(perf_counter()-start)

# download_image("", "https://cdn.polyhaven.com/asset_img/thumbs/grass_medium_01.png?width=125&height=125")