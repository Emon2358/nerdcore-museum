import os
import sys
import time
import re
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ダウンロードフォルダ
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# SoundCloud & Bandcamp のURLチェック
def is_supported_url(url):
    return "soundcloud.com" in url or "bandcamp.com" in url

# Selenium のセットアップ
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")

    driver = webdriver.Chrome(options=options)
    return driver

# SoundCloudのトラックURL取得 (Selenium)
def get_soundcloud_tracks(page_url):
    print(f"🔍 SoundCloudのページ解析中: {page_url}")

    driver = get_driver()
    driver.get(page_url)

    try:
        # JavaScript の読み込みを待つ
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # 追加の読み込み待機

        tracks = []
        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            href = link.get_attribute("href")
            if href and "/tracks/" in href:
                tracks.append(href)

        tracks = list(set(tracks))  # 重複を排除
        print(f"✅ {len(tracks)} 件のトラックを発見")
        return tracks
    except Exception as e:
        print(f"⚠️ SoundCloudの解析中にエラー発生: {e}")
        return []
    finally:
        driver.quit()

# BandcampのトラックURL取得
def get_bandcamp_tracks(page_url):
    print(f"🔍 Bandcampのページ解析中: {page_url}")

    driver = get_driver()
    driver.get(page_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # 追加の読み込み待機

        tracks = []
        page_source = driver.page_source

        matches = re.findall(r'"file":{"mp3-128":"(.*?)"}', page_source)
        for match in matches:
            tracks.append(match.replace("\\", ""))

        tracks = list(set(tracks))  # 重複を排除
        print(f"✅ {len(tracks)} 件のトラックを発見")
        return tracks
    except Exception as e:
        print(f"⚠️ Bandcampの解析中にエラー発生: {e}")
        return []
    finally:
        driver.quit()

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
