import os
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse
from app.schemas import LinkRequest
from app.services.downloader import process_instagram_url, download_instagram_video, cleanup_file

router = APIRouter()

@router.post("/download")
async def download_reel(request: LinkRequest, background_tasks: BackgroundTasks):
    raw_url = str(request.url).strip()
    clean_url = process_instagram_url(raw_url)
    filepath = download_instagram_video(clean_url)

    ext = os.path.splitext(filepath)[1]
    video_id = os.path.basename(filepath).split('.')[0]
    clean_filename = f"reel_{video_id}{ext}"

    background_tasks.add_task(cleanup_file, filepath)

    return FileResponse(
        path=filepath,
        filename=clean_filename,
        media_type="application/octet-stream"
    )
