#!/usr/bin/env python3
import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import yt_dlp
import logging

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
                    # 音楽ファイルの直接リンクまたは音楽ページへのリンクを検出
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
        }

        # ソースタイプに応じた追加設定
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
                ydl.download([url])
            return True
        except Exception as e:
            logger.error(f"ダウンロード中にエラーが発生: {str(e)}")
            return False

    def download_direct_link(self, url):
        """直接リンクからファイルをダウンロード"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # ファイル名を取得
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                # Content-Dispositionヘッダーからファイル名を取得
                cd = response.headers.get('content-disposition')
                if cd:
                    filename = re.findall("filename=(.+)", cd)[0]
                else:
                    filename = 'downloaded_file.mp3'
            
            file_path = os.path.join(self.filtered_dir, filename)
            
            # ファイルを保存
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
        
        # 内部リンクのスクレイピング
        urls_to_process = [url]
        if scrape_links:
            internal_links = self.get_internal_links(url)
            urls_to_process.extend(internal_links)
            logger.info(f"追加の内部リンクを {len(internal_links)} 個見つけました")
        
        # 各URLを処理
        success_count = 0
        for current_url in urls_to_process:
            if source_type == "direct_link":
                if self.download_direct_link(current_url):
                    success_count += 1
            else:
                if self.download_with_yt_dlp(current_url, source_type):
                    success_count += 1
        
        return success_count

def main():
    if len(sys.argv) < 4:
        print("使用方法: python downloader.py <URL> <SCRAPE_LINKS> <SOURCE_TYPE>")
        sys.exit(1)

    url = sys.argv[1]
    scrape_links = sys.argv[2].lower() == "true"
    source_type = sys.argv[3]

    downloader = MusicDownloader()
    success_count = downloader.process_url(url, scrape_links, source_type)
    
    logger.info(f"ダウンロード完了: {success_count} 個のファイルを処理しました")

if __name__ == "__main__":
    main()
