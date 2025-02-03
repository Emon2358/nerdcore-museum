import os
import re
import sys
import logging
import requests
import yt_dlp
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
from urllib.request import urlopen

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 無効な文字を置換する関数（Windows や Linux で禁止されている記号を除去）
def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)

# ダウンロードフォルダ
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class MusicDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'best',  # 自動で最適なフォーマットを選択
                'preferredquality': '192', # 高音質で保存
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'extract_flat': False,
            'noplaylist': False,
            'ignoreerrors': False,
            'quiet': False,
            'verbose': True
        }

    def download(self, url):
        try:
            logger.info(f"🎵 ダウンロード開始: {url}")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # ファイル名を整理
                sanitized_title = sanitize_filename(info.get('title', 'Unknown'))
                file_ext = info.get('ext', 'mp3')  # 自動判別
                new_filename = f"{sanitized_title}.{file_ext}"
                old_path = os.path.join(DOWNLOAD_DIR, info['_filename'])
                new_path = os.path.join(DOWNLOAD_DIR, new_filename)

                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                    logger.info(f"✅ ダウンロード完了: {new_filename}")

        except Exception as e:
            logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")

def main():
    if len(sys.argv) < 2:
        logger.error("❌ URLが指定されていません。")
        print("使用方法: python downloader.py <URL1> <URL2> ...")
        sys.exit(1)

    urls = sys.argv[1:]
    downloader = MusicDownloader()

    for url in urls:
        downloader.download(url)

if __name__ == "__main__":
    main()

