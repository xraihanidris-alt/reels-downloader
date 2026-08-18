import os
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def serve_gui():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
