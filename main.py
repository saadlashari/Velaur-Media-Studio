import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import yt_dlp
from yt_dlp.utils import download_range_func

app = FastAPI(title="Velaur Labs - Media Studio Core")

# Ye route add karein taake browser mein index.html direct khul jaye
@app.get("/")

@app.get("/favicon.ico")
def favicon():
    return FileResponse("logo.png")

@app.get("/index.html")
def read_index():
    return FileResponse("index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def parse_time_to_seconds(time_str: str) -> float:
    if not time_str:
        return 0.0
    try:
        parts = list(map(float, time_str.strip().split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except Exception:
        return 0.0
    return 0.0

@app.get("/api/info")
def get_media_info(url: str = Query(...)):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = None
            for f in reversed(info.get('formats', [])):
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url'):
                    stream_url = f.get('url')
                    break

            return {
                "title": info.get('title', 'Untitled Video'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration', 0),
                "duration_string": info.get('duration_string') or f"{info.get('duration', 0)}s",
                "uploader": info.get('uploader', 'Velaur Media Hub'),
                "url": url,
                "stream_url": stream_url or url
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/export")
def export_media(
    url: str,
    output_format: str = Query("mp4"),
    resolution: str = Query("1024"),
    quality: str = Query("high"),
    start_time: str = Query(None),
    end_time: str = Query(None)
):
    try:
        filename_template = os.path.join(DOWNLOAD_DIR, "velaur_%(id)s_%(epoch)s.%(ext)s")
        
        if output_format == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': filename_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320' if quality == 'high' else '192',
                }],
                'quiet': True,
                'force_keyframes_at_cuts': True
            }
        else:
            max_res = "720" if resolution == "720" else ("1080" if resolution == "1024" else "2160")
            ydl_opts = {
                'format': f"bestvideo[height<={max_res}]+bestaudio/best[height<={max_res}]/best",
                'outtmpl': filename_template,
                'merge_output_format': 'mp4',
                'quiet': True,
                'force_keyframes_at_cuts': True
            }

        if start_time and end_time:
            s_sec = parse_time_to_seconds(start_time)
            e_sec = parse_time_to_seconds(end_time)
            if e_sec > s_sec:
                ydl_opts['download_ranges'] = download_range_func(None, [(s_sec, e_sec)])

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)
            output_file = ydl.prepare_filename(meta)
            
            if output_format == "mp3":
                output_file = os.path.splitext(output_file)[0] + ".mp3"
            elif not output_file.endswith('.mp4'):
                output_file = os.path.splitext(output_file)[0] + ".mp4"

            if os.path.exists(output_file):
                safe_title = "".join(c for c in meta.get('title', 'velaur_export') if c.isalnum() or c in (' ', '_', '-')).strip()
                final_filename = f"{safe_title}_{start_time or 'full'}.{output_format}".replace(":", "-")
                return FileResponse(
                    path=output_file,
                    filename=final_filename,
                    media_type='application/octet-stream'
                )
            else:
                raise HTTPException(status_code=500, detail="Processed file not found.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
