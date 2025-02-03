#!/usr/bin/env python3
import sys
import os
import re
import requests
import shutil
import yt_dlp
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MusicDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = output_dir
        self.filtered_dir = os.path.join(output_dir, "filtered")
        self.ensure_directories()

    def ensure_directories(self):
        """必要なディレクトリを作成"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.filtered_dir, exist_ok=True)

    def detect_source_type(self, url):
        """URLからソースタイプを自動検出"""
        domain = urlparse(url).netloc.lower()
        if "soundcloud.com" in domain:
            return "soundcloud"
        elif "bandcamp.com" in domain:
            return "bandcamp"
        elif "archive.org" in domain:
            return "archive"
        else:
            return "direct_link"

    def get_internal_links(self, url):
        """ページ内の関連する内部リンクを取得"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            base_domain = urlparse(url).netloc
            
            internal_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                if urlparse(full_url).netloc == base_domain:
                    if any(ext in href.lower() for ext in ['.mp3', '.wav', '.flac', '.m4a']):
                        internal_links.append(full_url)
                    elif any(keyword in href.lower() for keyword in ['/track/', '/album/', '/music/', '/song/']):
                        internal_links.append(full_url)
            
            return internal_links
        except Exception as e:
            logger.error(f"内部リンクの取得中にエラーが発生: {str(e)}")
            return []

    def download_with_yt_dlp(self, url, source_type):
        """yt-dlpを使用して音楽をダウンロード"""
        # URLをエンコード
        encoded_url = quote(url, safe=':/')

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.filtered_dir, '%(title)s.%(ext)s'),
            'verbose': True,
            'quiet': False,
            'no_warnings': False,
            'http_headers': {
                'User -Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 Safari/537.36',
                'Referer': url  # リファラーを設定
            }
        }

        if source_type == "soundcloud":
            ydl_opts.update({
                'extract_flat': 'in_playlist',
            })
        elif source_type == "bandcamp":
            ydl_opts.update({
                'extract_flat': 'in_playlist',
                'write_thumbnail': False,
            })
        elif source_type == "archive":
            ydl_opts.update({
                'extract_flat': False,
                'ignore_errors': True,
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download ([encoded_url])  # 修正された行
            return True
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"ダウンロード中にエラーが発生: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"予期しないエラーが発生: {str(e)}")
            return False

    def download_direct_link(self, url):
        """直接リンクからファイルをダウンロード"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                cd = response.headers.get('content-disposition')
                if cd:
                    filename = re.findall("filename=(.+)", cd)[0]
                else:
                    filename = 'downloaded_file.mp3'
            
            file_path = os.path.join(self.filtered_dir, filename)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"直接ダウンロード中にエラーが発生: {str(e)}")
            return False

    def process_url(self, url, scrape_links=False, source_type="auto_detect"):
        """URLを処理してダウンロードを実行"""
        if source_type == "auto_detect":
            source_type = self.detect_source_type(url)
        
        logger.info(f"ダウンロードを開始: {url} (タイプ: {source_type})")
        
        urls_to_process = [url]
        if scrape_links:
            internal_links = self.get_internal_links(url)
            urls_to_process.extend(internal_links)
            logger.info(f"追加の内部リンクを {len(internal_links)} 個見つけました")
        
        success_count = sum(self.download_with_yt_dlp(u, source_type) for u in urls_to_process)
        return success_count

def main():
    if len(sys.argv) < 4:
        print("使用方法: python downloader.py <URL> <SCRAPE_LINKS> <SOURCE_TYPE>")
        sys.exit(1)

    downloader = MusicDownloader()
    success_count = downloader.process_url(sys.argv[1], sys.argv[2].lower() == "true", sys.argv[3])
    
    logger.info(f"ダウンロード完了: {success_count} 個のファイルを処理しました")

if __name__ == "__main__":
    main()
