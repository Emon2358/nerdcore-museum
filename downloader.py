import os
import sys
import re
import subprocess
import requests
from bs4 import BeautifulSoup

# ダウンロードフォルダ
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# SoundCloud & Bandcamp のURLチェック
def is_supported_url(url):
    return "soundcloud.com" in url or "bandcamp.com" in url

# 音楽をダウンロード
def download_track(url):
    if not is_supported_url(url):
        print("❌ SoundCloud または Bandcamp の URL ではありません:", url)
        return None

    print(f"🎵 ダウンロード中: {url}")

    command = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "wav",
        "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        url
    ]
    
    try:
        subprocess.run(command, check=True)
        print("✅ ダウンロード完了!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ エラーが発生しました: {e}")

# SoundCloudのトラックURL取得
def get_soundcloud_tracks(page_url):
    print(f"🔍 SoundCloudのページ解析中: {page_url}")
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, "html.parser")

    tracks = []
    for link in soup.find_all("a", href=True):
        if "/tracks/" in link["href"]:
            track_url = f"https://soundcloud.com{link['href']}"
            tracks.append(track_url)

    return list(set(tracks))

# BandcampのトラックURL取得
def get_bandcamp_tracks(page_url):
    print(f"🔍 Bandcampのページ解析中: {page_url}")
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, "html.parser")

    tracks = []
    for script in soup.find_all("script"):
        if "trackinfo" in script.text:
            match = re.search(r'"file":{"mp3-128":"(.*?)"}', script.text)
            if match:
                track_url = match.group(1).replace("\\", "")
                tracks.append(track_url)

    return list(set(tracks))

# メイン処理
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ URL が指定されていません。")
        sys.exit(1)

    url = sys.argv[1]

    if "soundcloud.com" in url:
        tracks = get_soundcloud_tracks(url)
    elif "bandcamp.com" in url:
        tracks = get_bandcamp_tracks(url)
    else:
        print("🚫 対応していない URL です。")
        sys.exit(1)

    if not tracks:
        print("🚫 トラックが見つかりませんでした。")
    else:
        for track in tracks:
            download_track(track)
