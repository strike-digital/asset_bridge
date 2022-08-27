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
