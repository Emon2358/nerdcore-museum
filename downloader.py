import os
import sys
import yt_dlp
import logging
import requests
from bs4 import BeautifulSoup

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
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'extract_flat': False,
            'noplaylist': False,
            'ignoreerrors': False,
            'quiet': False,
            'verbose': True
        }

    def download(self, url, scrape_internal_links=False):
        """指定されたURLからトラックをダウンロード"""
        try:
            logger.info(f"🎵 解析とダウンロードを開始: {url}")
            
            if scrape_internal_links:
                internal_links = self.scrape_internal_links(url)
                for link in internal_links:
                    self.download_track(link)
            else:
                self.download_track(url)
                
            return True
            
        except Exception as e:
            logger.error(f"⚠️ 予期せぬエラーが発生: {str(e)}")
            return False

    def scrape_internal_links(self, url):
        """指定されたURLから内部リンクをスクレイピング"""
        logger.info(f"🔍 内部リンクをスクレイピング中: {url}")
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            if a['href'].endswith('.mp3'):
                links.append(a['href'])
        
        logger.info(f"✨ 見つかった内部リンク: {links}")
        return links

    def download_track(self, url):
        """トラックをダウンロード"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                logger.info(f"✅ トラック「{info.get('title', 'Unknown')}」のダウンロードが完了しました！")
            except Exception as e:
                logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")

def main():
    if len(sys.argv) < 3:
        logger.error("❌ URLとダウンロード方法が指定されていません。")
        print("使用方法: python downloader.py <URL> <scrape_internal_links>")
        sys.exit(1)

    url = sys.argv[1]
    scrape_internal_links = sys.argv[2].lower() == 'true'
    downloader = MusicDownloader()
    
    # URLの検証
    if not ("soundcloud.com" in url or "bandcamp.com" in url):
        logger.error("🚫 SoundCloudまたはBandcampのURLを指定してください。")
        sys.exit(1)
    
    success = downloader.download(url, scrape_internal_links)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
