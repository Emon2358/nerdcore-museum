import os
import re
import sys
import logging
import requests
import yt_dlp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
from urllib.request import urlopen

# ロギング設定
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
                if name == 'href' and (value.endswith('.mp3') or value.endswith('.wav') or value.endswith('.m4a')):
                    full_url = urljoin(self.base_url, value)
                    self.links.append(full_url)

class VKLinkParser:
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_html(self):
        response = self.session.get(self.url, headers=self.headers)
        response.raise_for_status()
        return response.text

    def scrape_internal_links(self):
        html = self.get_html()
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', class_='vkuiLink'):
            href = a_tag.get('href', '')
            file_type = a_tag.find('span', class_='vkitChipAttachment__nowrap--Uv0dn')
            
            if href and file_type and '.zip' in file_type.text:
                full_url = urljoin(self.url, href)
                links.append(full_url)
        
        return links

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
        try:
            logger.info(f"🎵 解析とダウンロードを開始: {url}")
            
            if source_type == 'auto_detect':
                source_type = self.detect_source_type(url)
            
            internal_links = []
            if scrape_internal_links or source_type in ['archive', 'vk']:
                internal_links = self.scrape_internal_links(url, source_type)
            
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
        elif 'vk.com' in url:
            return 'vk'
        else:
            return 'direct_link'

    def scrape_internal_links(self, url, source_type):
        logger.info(f"🔍 内部リンクをスクレイピング中: {url}")
        
        if source_type == 'archive':
            try:
                with urlopen(url) as response:
                    html = response.read().decode('utf-8')
            except Exception as e:
                logger.error(f"URLを開けませんでした: {e}")
                return []
            parser = LinkParser(url)
            parser.feed(html)
            return parser.links
        
        elif source_type == 'vk':
            vk_parser = VKLinkParser(url)
            return vk_parser.scrape_internal_links()
        
        return []

    def download_track(self, url):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                logger.info(f"✅ トラック「{info.get('title', 'Unknown')}」のダウンロードが完了しました！")
            except Exception as e:
                logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")

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
