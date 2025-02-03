import os
import sys
import yt_dlp
import logging
import shutil
from urllib.request import urlopen
from urllib.parse import urljoin
from html.parser import HTMLParser

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ダウンロードフォルダ
BASE_DOWNLOAD_DIR = "downloads"
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

class LinkParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and (
                    value.endswith('.mp3') or 
                    value.endswith('.wav') or  
                    value.endswith('.m4a')
                ):
                    full_url = urljoin(self.base_url, value)
                    self.links.append(full_url)

class MusicDownloader:
    def __init__(self, output_dir):
        self.output_dir = os.path.join(BASE_DOWNLOAD_DIR, output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.output_dir}/%(title)s.%(ext)s',
            'extract_flat': False,
            'noplaylist': False,
            'ignoreerrors': False,
            'quiet': False,
            'verbose': True
        }

    def download(self, url, scrape_internal_links=False, source_type='auto_detect'):
        try:
            logger.info(f"🎵 解析とダウンロードを開始: {url}")
            if source_type == 'auto_detect':
                source_type = self.detect_source_type(url)
            
            internal_links = []
            if scrape_internal_links or source_type == 'archive':
                internal_links = self.scrape_internal_links(url)
            
            self.download_track(url)
            for link in internal_links:
                self.download_track(link)
            return True
        except Exception as e:
            logger.error(f"⚠️ 予期せぬエラー: {str(e)}")
            return False

    def detect_source_type(self, url):
        if 'archive.org' in url:
            return 'archive'
        elif 'soundcloud.com' in url:
            return 'soundcloud'
        elif 'bandcamp.com' in url:
            return 'bandcamp'
        else:
            return 'direct_link'

    def scrape_internal_links(self, url):
        logger.info(f"🔍 内部リンクを取得: {url}")
        try:
            with urlopen(url) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            logger.error(f"URL取得失敗: {e}")
            return []
        parser = LinkParser(url)
        parser.feed(html)
        return parser.links

    def download_track(self, url):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                logger.info(f"✅ ダウンロード完了: {info.get('title', 'Unknown')}")
            except Exception as e:
                logger.error(f"⚠️ ダウンロードエラー: {str(e)}")

    def create_zip(self, zip_name):
        zip_path = os.path.join(BASE_DOWNLOAD_DIR, f"{zip_name}.zip")
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', self.output_dir)
        logger.info(f"📦 ZIP作成: {zip_path}")
        return zip_path

def main():
    if len(sys.argv) < 5:
        logger.error("❌ 必須引数が不足しています。")
        print("使用: python downloader.py <ZIP名> <URL1> <URL2> ... <scrape_internal_links> <source_type>")
        sys.exit(1)
    
    zip_name = sys.argv[1]
    scrape_internal_links = sys.argv[-2].lower() == 'true'
    source_type = sys.argv[-1]
    urls = sys.argv[2:-2]
    
    downloader = MusicDownloader(zip_name)
    
    for url in urls:
        success = downloader.download(url, scrape_internal_links, source_type)
        if not success:
            logger.error(f"❌ {url} のダウンロード失敗。")
    
    zip_path = downloader.create_zip(zip_name)
    logger.info(f"✅ 完了: {zip_path}")

if __name__ == "__main__":
    main()
