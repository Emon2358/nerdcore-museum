import os
import sys
import yt_dlp
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ダウンロードフォルダ
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class MusicDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': True,
            'noplaylist': True,
            'force_generic_extractor': True,
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }]
        }

    def get_driver(self):
        """Seleniumドライバーのセットアップ"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        
        # Chromiumのパスを明示的に指定
        options.binary_location = "/usr/bin/chromium-browser"
        
        # ChromeDriverのパスを指定
        service = Service("/usr/bin/chromedriver")
        
        return webdriver.Chrome(service=service, options=options)

    def get_track_info(self, url):
        """URLからトラック情報を取得"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info['title'],
                    'url': info['url'],
                    'thumbnail': info.get('thumbnail', '')
                }
        except Exception as e:
            logger.error(f"トラック情報の取得中にエラーが発生: {str(e)}")
            return None

    def download_track(self, url):
        """トラックをダウンロード"""
        try:
            logger.info(f"🎵 ダウンロード開始: {url}")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([url])
            logger.info("✅ ダウンロード完了!")
            return True
        except Exception as e:
            logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")
            return False

    def get_bandcamp_tracks(self, page_url):
        """Bandcampページからトラックを取得"""
        logger.info(f"🔍 Bandcampのページ解析中: {page_url}")
        driver = self.get_driver()
        tracks = []

        try:
            driver.get(page_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # 追加の読み込み待機

            page_source = driver.page_source
            matches = re.findall(r'"file":{"mp3-128":"(.*?)"}', page_source)
            tracks = [match.replace("\\", "") for match in matches]
            tracks = list(set(tracks))  # 重複を排除

            logger.info(f"✅ {len(tracks)} 件のトラックを発見")
            return tracks

        except Exception as e:
            logger.error(f"⚠️ Bandcampの解析中にエラー発生: {str(e)}")
            return []
        finally:
            driver.quit()

    def get_soundcloud_tracks(self, page_url):
        """SoundCloudページからトラックを取得"""
        logger.info(f"🔍 SoundCloudのページ解析中: {page_url}")
        driver = self.get_driver()
        tracks = []

        try:
            driver.get(page_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)

            links = driver.find_elements(By.TAG_NAME, "a")
            tracks = [link.get_attribute("href") for link in links if link.get_attribute("href") and "/tracks/" in link.get_attribute("href")]
            tracks = list(set(tracks))

            logger.info(f"✅ {len(tracks)} 件のトラックを発見")
            return tracks

        except Exception as e:
            logger.error(f"⚠️ SoundCloudの解析中にエラー発生: {str(e)}")
            return []
        finally:
            driver.quit()

def main():
    if len(sys.argv) < 2:
        logger.error("❌ URLが指定されていません。")
        sys.exit(1)

    url = sys.argv[1]
    downloader = MusicDownloader()

    if "soundcloud.com" in url:
        tracks = downloader.get_soundcloud_tracks(url)
    elif "bandcamp.com" in url:
        tracks = downloader.get_bandcamp_tracks(url)
    else:
        logger.error("🚫 対応していないURLです。")
        sys.exit(1)

    if not tracks:
        logger.error("🚫 トラックが見つかりませんでした。")
        sys.exit(1)

    for track in tracks:
        downloader.download_track(track)

if __name__ == "__main__":
    main()
