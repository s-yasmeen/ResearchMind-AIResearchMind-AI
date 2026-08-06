import os
import requests


class PDFDownloader:

    @staticmethod
    def download(url, filename):

        os.makedirs("papers", exist_ok=True)

        path = os.path.join("papers", filename)

        if os.path.exists(path):
            return path

        print("Downloading:", filename)

        r = requests.get(url, timeout=60)
        r.raise_for_status()

        with open(path, "wb") as f:
            f.write(r.content)

        return path