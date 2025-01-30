import os
import sys
import yt_dlp
import logging

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
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            # プレイリストを許可
            'extract_flat': False,
            'noplaylist': False,
            # エラーハンドリングの改善
            'ignoreerrors': False,
            'quiet': False,
            'verbose': True
        }

    def download(self, url):
        """指定されたURLからトラックをダウンロード"""
        try:
            logger.info(f"🎵 解析とダウンロードを開始: {url}")
            
            # まず情報を取得してプレイリストかどうかを確認
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    
                    if info is None:
                        logger.error("❌ URLの情報を取得できませんでした。")
                        return False
                    
                    # プレイリストの場合
                    if 'entries' in info:
                        logger.info(f"✨ プレイリスト「{info.get('title', 'Unknown')}」を検出: {len(info['entries'])} トラック")
                        # ダウンロードを実行
                        ydl.download([url])
                        logger.info("✅ プレイリストのダウンロードが完了しました！")
                    # 単曲の場合
                    else:
                        logger.info(f"✨ トラック「{info.get('title', 'Unknown')}」を検出")
                        # ダウンロードを実行
                        ydl.download([url])
                        logger.info("✅ トラックのダウンロードが完了しました！")
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"⚠️ ダウンロード中にエラーが発生: {str(e)}")
                    return False
                
        except Exception as e:
            logger.error(f"⚠️ 予期せぬエラーが発生: {str(e)}")
            return False

def main():
    if len(sys.argv) < 2:
        logger.error("❌ URLが指定されていません。")
        print("使用方法: python downloader.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    downloader = MusicDownloader()
    
    # URLの検証
    if not ("soundcloud.com" in url or "bandcamp.com" in url):
        logger.error("🚫 SoundCloudまたはBandcampのURLを指定してください。")
        sys.exit(1)
    
    success = downloader.download(url)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
