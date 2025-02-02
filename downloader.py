#!/usr/bin/env python3
import sys
import os
import re
import requests
import subprocess
import shutil
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
        self.torrent_dir = os.path.join(output_dir, "torrents")
        self.ensure_directories()

    def ensure_directories(self):
        """必要なディレクトリを作成"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.filtered_dir, exist_ok=True)
        os.makedirs(self.torrent_dir, exist_ok=True)

    def detect_source_type(self, url):
        """URLからソースタイプを自動検出"""
        if url.startswith('magnet:'):
            return "torrent"
        if url.lower().endswith('.torrent'):
            return "torrent"
            
        domain = urlparse(url).netloc.lower()
        if "soundcloud.com" in domain:
            return "soundcloud"
        elif "bandcamp.com" in domain:
            return "bandcamp"
        elif "archive.org" in domain:
            return "archive"
        else:
            return "direct_link"

    def download_torrent(self, url):
        """トレントまたはマグネットリンクをダウンロード"""
        try:
            # aria2cコマンドの基本オプション
            aria2c_options = [
                '--dir=' + self.output_dir,
                '--seed-time=0',
                '--max-connection-per-server=16',
                '--split=16',
                '--min-split-size=1M',
                '--max-overall-download-limit=0',
                '--max-download-limit=0',
                '--bt-max-peers=200',
                '--bt-request-peer-speed-limit=0',
                '--bt-enable-lpd=true',
                '--bt-tracker-connect-timeout=5',
                '--bt-tracker-timeout=10',
                '--bt-seed-unverified=true',
                '--enable-dht=true',
                '--dht-listen-port=6881',
                '--file-allocation=none'
            ]

            # マグネットリンクまたはトレントファイルの処理
            if url.startswith('magnet:'):
                logger.info(f"マグネットリンクのダウンロードを開始: {url}")  # ここでログを出す
                cmd = ['aria2c'] + aria2c_options + [url]
            else:
                logger.info("トレントファイルのダウンロードを開始")
                torrent_path = os.path.join(self.torrent_dir, 'download.torrent')
                # トレントファイルをダウンロード
                response = requests.get(url)
                response.raise_for_status()
                with open(torrent_path, 'wb') as f:
                    f.write(response.content)
                cmd = ['aria2c'] + aria2c_options + [torrent_path]

            # aria2cを実行
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"aria2c error: {stderr}")

            # ダウンロードしたファイルを検索して filtered ディレクトリに移動
            music_files = []
            for root, _, files in os.walk(self.output_dir):
                for file in files:
                    if file.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(self.filtered_dir, file)
                        shutil.move(src_path, dst_path)
                        music_files.append(dst_path)

            return len(music_files) > 0

        except Exception as e:
            logger.error(f"トレントダウンロード中にエラーが発生: {str(e)}")
            return False

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
                logger.info(f"yt-dlpでダウンロードを開始: {url}")
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
            
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                cd = response.headers.get('content-disposition')
                if cd:
                    filename = re.findall("filename=(.+)", cd)[0]
                else:
                    filename = 'downloaded_file.mp3'
            
            file_path = os.path.join(self.filtered_dir, filename)
            logger.info(f"直接ダウンロード中: {filename} を {file_path} に保存")

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
        
        if source_type == "torrent":
            return 1 if self.download_torrent(url) else 0
        
        urls_to_process = [url]
        if scrape_links:
            internal_links = self.get_internal_links(url)
            urls_to_process.extend(internal_links)
            logger.info(f"追加の内部リンクを {len(internal_links)} 個見つけました")
        
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
