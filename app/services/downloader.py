import os
import glob
import re
from urllib.parse import urlparse
from fastapi import HTTPException
import yt_dlp
from app.config import DOWNLOAD_DIR

def cleanup_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)

def process_instagram_url(raw_url: str) -> str:
    if len(raw_url) > 200:
        raise HTTPException(status_code=400, detail="URL is too long.")

    parsed = urlparse(raw_url)
    if "instagram.com" not in parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid website. Please paste an Instagram link.")

    pattern = r"^/(reel|p|tv)/([A-Za-z0-9_-]+)/?"
    match = re.search(pattern, parsed.path)

    if not match:
        raise HTTPException(status_code=400, detail="Invalid Reel link structure.")

    return f"https://www.instagram.com{match.group(0)}"

def download_instagram_video(clean_url: str) -> str:
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            video_id = info.get("id")

        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}.*"))
        if not files:
            raise HTTPException(status_code=500, detail="Unable to process video.")

        filepath = files[0]
        ext = os.path.splitext(filepath)[1]

        if ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
            cleanup_file(filepath)
            raise HTTPException(status_code=400, detail="Photos are not supported.")

        return filepath

    except yt_dlp.utils.DownloadError as err:
        err_msg = str(err).lower()
        if "private" in err_msg or "login" in err_msg:
            detail = "This Reel is from a private account."
        elif "404" in err_msg:
            detail = "Video not found or deleted."
        else:
            detail = "Could not download video."
        raise HTTPException(status_code=400, detail=detail)
