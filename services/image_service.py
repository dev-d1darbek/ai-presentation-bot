import os
import requests
from config import PEXELS_API_KEY
from loguru import logger

class ImageService:
    @staticmethod
    def get_pexels_image(query: str, save_path: str) -> bool:
        if not PEXELS_API_KEY:
            return False
        try:
            headers = {"Authorization": PEXELS_API_KEY}
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                if photos:
                    img_url = photos[0]["src"]["large"]
                    img_data = requests.get(img_url, timeout=10).content
                    with open(save_path, "wb") as f:
                        f.write(img_data)
                    return True
        except Exception as e:
            logger.warning(f"Pexels image download failed: {e}")
        return False

    @classmethod
    def fetch_image(cls, query: str, save_path: str) -> bool:
        # Егер Pexels кілті жоқ болса, сурет жүктеуге тырыспайды (қате бермейді)
        if not PEXELS_API_KEY:
            return False
        return cls.get_pexels_image(query, save_path)