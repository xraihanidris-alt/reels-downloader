import os
import glob
import re
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def serve_gui():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found</h1>"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DOWNLOAD_DIR = "temp_downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class LinkRequest(BaseModel):
    url: str

def cleanup_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)

@app.post("/download")
async def download_reel(request: LinkRequest, background_tasks: BackgroundTasks):
    raw_url = request.url.strip()
    
    if not raw_url:
        raise HTTPException(status_code=400, detail="Please paste a link first.")

    if len(raw_url) > 200:
        raise HTTPException(status_code=400, detail="URL is too long (maximum 200 characters).")

    parsed = urlparse(raw_url)
    if "instagram.com" not in parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid website. Please paste an Instagram link.")

    pattern = r"^/(reel|p|tv)/([A-Za-z0-9_-]+)/?"
    match = re.search(pattern, parsed.path)

    if not match:
        raise HTTPException(status_code=400, detail="Invalid Reel link structure. Please paste a clean Reel link.")

    clean_url = f"https://www.instagram.com{match.group(0)}"

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
            raise HTTPException(status_code=500, detail="Unable to process video. It may be private or deleted.")

        filepath = files[0]
        ext = os.path.splitext(filepath)[1]

        if ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
            cleanup_file(filepath)
            raise HTTPException(status_code=400, detail="This link contains a photo. Only Instagram Reels/videos are supported.")

        clean_filename = f"reel_{video_id}{ext}"
        background_tasks.add_task(cleanup_file, filepath)

        return FileResponse(
            path=filepath,
            filename=clean_filename,
            media_type="application/octet-stream"
        )

    except yt_dlp.utils.DownloadError as err:
        err_msg = str(err).lower()
        if "private" in err_msg or "login" in err_msg:
            detail = "This Reel is from a private account."
        elif "404" in err_msg:
            detail = "Video not found. It may have been deleted."
        else:
            detail = "Could not download video. Please check the link."
        raise HTTPException(status_code=400, detail=detail)

    except HTTPException as http_err:
        raise http_err

    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong on our server.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
