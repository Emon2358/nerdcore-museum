import os
import sys
import yt_dlp
import logging
import zipfile
import shutil
from urllib.request import urlopen, urlretrieve
from urllib.parse import urljoin
from html.parser import HTMLParser

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ダウンロードフォルダ
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

    def download(self, url, scrape_internal_links=False, source_type='auto_detect'):
        """指定されたURLからトラックをダウンロード"""
        try:
            logger.info(f"🎵 解析とダウンロードを開始: {url}")
            
            if url.endswith('.zip'):
                return self.download_and_extract_zip(url)
            
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
            logger.error(f"⚠️ 予期せぬエラーが発生: {str(e)}")
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
        logger.info(f"🔍 内部リンクをスクレイピング中: {url}")
        
        try:
            with urlopen(url) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            logger.error(f"URLを開けませんでした: {e}")
            return []

        parser = LinkParser(url)
        parser.feed(html)
        
        logger.info(f"✨ 見つかった内部リンク: {parser.links}")
        return parser.links

    def download_track(self, url):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                logger.info(f"✅ トラック「{info.get('title', 'Unknown')}」のダウンロードが完了しました！")
            except Exception as e:
                logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")

    def download_and_extract_zip(self, url):
        """ZIPファイルをダウンロードして解凍"""
        try:
            zip_path = os.path.join(DOWNLOAD_DIR, os.path.basename(url))
            extract_path = os.path.join(DOWNLOAD_DIR, os.path.splitext(os.path.basename(url))[0])
            
            logger.info(f"📥 ZIPファイルをダウンロード中: {url}")
            urlretrieve(url, zip_path)
            
            logger.info(f"📂 ZIPファイルを解凍中: {zip_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            os.remove(zip_path)
            logger.info(f"✅ ZIPファイルの処理が完了: {extract_path}")
            return True
        except Exception as e:
            logger.error(f"❌ ZIPの処理に失敗: {str(e)}")
            return False

def main():
    if len(sys.argv) < 4:
        logger.error("❌ URLとダウンロード方法、ソースタイプが指定されていません。")
        print("使用方法: python downloader.py <URL1> <URL2> ... <scrape_internal_links> <source_type>")
        sys.exit(1)

    scrape_internal_links = sys.argv[-2].lower() == 'true'
    source_type = sys.argv[-1]
    urls = sys.argv[1:-2]

    downloader = MusicDownloader()
    
    for url in urls:
        success = downloader.download(url, scrape_internal_links, source_type)
        if not success:
            logger.error(f"❌ {url} のダウンロードに失敗しました。")

if __name__ == "__main__":
    main()
