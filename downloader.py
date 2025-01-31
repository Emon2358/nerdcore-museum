import os
import sys
import yt_dlp
import logging
from urllib.request import urlopen
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
                    value.endswith('.flac') or 
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
            
            # ソースタイプの判定
            if source_type == 'auto_detect':
                source_type = self.detect_source_type(url)
            
            # ソースタイプに基づいたダウンロード
            if source_type in ['soundcloud', 'bandcamp', 'direct_link']:
                if not any(platform in url for platform in ['soundcloud.com', 'bandcamp.com']):
                    logger.error("🚫 SoundCloudまたはBandcampのURLを指定してください。")
                    return False
            
            if scrape_internal_links or source_type == 'archive':
                internal_links = self.scrape_internal_links(url)
                for link in internal_links:
                    self.download_track(link)
            else:
                self.download_track(url)
                
            return True
            
        except Exception as e:
            logger.error(f"⚠️ 予期せぬエラーが発生: {str(e)}")
            return False

    def detect_source_type(self, url):
        """URLからソースタイプを自動検出"""
        if 'archive.org' in url:
            return 'archive'
        elif 'soundcloud.com' in url:
            return 'soundcloud'
        elif 'bandcamp.com' in url:
            return 'bandcamp'
        else:
            return 'direct_link'

    def scrape_internal_links(self, url):
        """指定されたURLから内部リンクをスクレイピング"""
        logger.info(f"🔍 内部リンクをスクレイピング中: {url}")
        
        # URLからHTMLを取得
        try:
            with urlopen(url) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            logger.error(f"URLを開けませんでした: {e}")
            return []

        # リンクを解析
        parser = LinkParser(url)
        parser.feed(html)
        
        logger.info(f"✨ 見つかった内部リンク: {parser.links}")
        return parser.links

    def download_track(self, url):
        """トラックをダウンロード"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                logger.info(f"✅ トラック「{info.get('title', 'Unknown')}」のダウンロードが完了しました！")
            except Exception as e:
                logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")

def main():
    if len(sys.argv) < 4:
        logger.error("❌ URLとダウンロード方法、ソースタイプが指定されていません。")
        print("使用方法: python downloader.py <URL> <scrape_internal_links> <source_type>")
        sys.exit(1)

    url = sys.argv[1]
    scrape_internal_links = sys.argv[2].lower() == 'true'
    source_type = sys.argv[3]

    downloader = MusicDownloader()
    
    success = downloader.download(url, scrape_internal_links, source_type)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
