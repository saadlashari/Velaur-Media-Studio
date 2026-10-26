"""Velaur Media Studio: background jobs, relayed previews and reusable metadata.
Run ONE uvicorn worker. Jobs and completed files survive an application restart.
"""
import copy
import hashlib
import ipaddress
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

import yt_dlp
from fastapi import FastAPI, File, Form, HTTPException, Query, Request as WebRequest, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel
from yt_dlp.utils import download_range_func
import accounts as accounts
from identity import router as identity_router, AccountGuard

BASE = Path(__file__).resolve().parent
DOWNLOADS = Path(os.getenv("DOWNLOAD_DIR", str(BASE / "downloads"))).resolve()
JOBS_DIR = DOWNLOADS / "jobs"
SOURCE_CACHE_DIR = DOWNLOADS / "source-cache"
YTDLP_CACHE_DIR = DOWNLOADS / "yt-dlp-cache"
for directory in (JOBS_DIR, SOURCE_CACHE_DIR, YTDLP_CACHE_DIR):
    directory.mkdir(parents=True, exist_ok=True)
# Source reuse is deliberately session-scoped. Remove orphaned private media
# left by a forced container restart; yt-dlp's non-media extractor cache stays.
for stale_cache in SOURCE_CACHE_DIR.iterdir():
    if stale_cache.is_dir():
        shutil.rmtree(stale_cache, ignore_errors=True)
    else:
        stale_cache.unlink(missing_ok=True)
COOKIE_FILE = os.getenv("COOKIE_FILE", "/app/cookies.txt")
META_COOKIE_FILE = os.getenv("META_COOKIE_FILE", "/app/meta-cookies.txt")
TIKTOK_RESOLVER = os.getenv("TIKTOK_RESOLVER", "tikwm").lower()
TIKTOK_PROXY = os.getenv("TIKTOK_PROXY", "")
log = logging.getLogger("uvicorn.error")
pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="velaur")
prefetch_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="velaur-prefetch")
lock = threading.RLock()
jobs = {}
metadata_cache = {}
streams = {}
preview_cache = {}
source_cache = {}
source_fetches = {}
SOURCE_CACHE_TTL = 15 * 60
app = FastAPI(title="VELAUR Media Studio", version="4.0", docs_url=None, redoc_url=None, openapi_url=None)
SITE_URL = "https://mediastudio.velaurlabs.com"
app.include_router(identity_router)
# admin-user-controls-1
from admin_tools import router as admin_tools_router
app.include_router(admin_tools_router)
app.add_middleware(AccountGuard)

@app.on_event("startup")
def initialize_accounts():
    accounts.initialize()



def save_job(job_id, **changes):
    with lock:
        job = jobs[job_id]
        owner = job.get("_owner")
        if owner and changes.get("state") != "error" and time.time() - job.get("_checked", 0) > 2:
            with accounts.tx() as connection:
                accounts.get_user(connection, owner)
            job["_checked"] = time.time()
        if changes.get("state") == "done" and owner:
            actual = None
            if job["kind"] == "export":
                actual = float(probe_video(Path(changes["_file"]))["format"]["duration"])
            accounts.finish(job_id, "done", actual)
        job.update(changes, updated=time.time())
        path = JOBS_DIR / job_id / "status.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)


# Restore completed files; interrupted processing must be retried after a restart.
for status_path in JOBS_DIR.glob("*/status.json"):
    try:
        job = json.loads(status_path.read_text(encoding="utf-8"))
        if job.get("state") in {"queued", "running"}:
            job.update(state="error", stage="Interrupted by server restart. Please retry.")
            job["error"] = job["stage"]
        jobs[job["id"]] = job
    except (ValueError, OSError, KeyError):
        log.warning("Could not restore a previous job")


def public_job(job):
    return {k: v for k, v in job.items() if not k.startswith("_")}


def check_url(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Enter a valid public http or https video link.")
        if parsed.port not in {None, 80, 443}:
            raise ValueError("Only standard web ports are supported.")
        # Exclude localhost/cloud metadata endpoints from a public downloader.
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Private and local network links are not supported.")
    except (ValueError, OSError) as exc:
        raise ValueError("Video link is invalid or its host cannot be reached.") from exc
    return url


def is_tiktok(url):
    host = (urlsplit(url).hostname or "").lower()
    return host == "tiktok.com" or host.endswith(".tiktok.com")


def timestamp(value):
    if not value:
        return None
    try:
        parts = [float(p) for p in str(value).split(":")]
        if len(parts) > 3 or any(p < 0 for p in parts):
            raise ValueError()
        result = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
        if not __import__("math").isfinite(result):
            raise ValueError()
        return result
    except ValueError:
        raise ValueError("Invalid start or end timestamp.")


def clip_range(start, end, duration=None):
    start = timestamp(start)
    end = timestamp(end)
    if start is None and end is None:
        return None
    start = start or 0
    if end is not None and end <= start:
        raise ValueError("End timestamp must be later than the start.")
    if duration and (start >= duration or (end is not None and end > duration + 1)):
        raise ValueError("Trim timestamps are outside this video's duration.")
    # A full-range export should not invoke an expensive clipping operation.
    if start == 0 and (end is None or (duration and end >= duration - 1)):
        return None
    return (start, end)


def resolution_height(value):
    return {"720": 720, "1024": 1080, "1080": 1080, "2048": 2160, "2160": 2160}.get(str(value), 1080)


def is_instagram_source(url):
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host == "instagram.com" or host.endswith(".instagram.com")

def ydl_options(url="", **overrides):
    if is_instagram_source(url):
        options = {
            "noplaylist": True,
        "geo_bypass": True,
        "geo_bypass_country": "US",
        "extractor_args": {
            "youtube": {"player_client": ["android", "web", "mweb"]}
        }, "quiet": True, "no_warnings": False,
            "socket_timeout": 20, "retries": 1, "extractor_retries": 1,
        }
        options.update(overrides)
        return options
    options = {
        "noplaylist": True, "quiet": True, "no_warnings": False,
        "socket_timeout": 15, "retries": 2, "extractor_retries": 1,
        "fragment_retries": 2, "concurrent_fragment_downloads": 4,
        "cachedir": str(YTDLP_CACHE_DIR),
    }
    cookie_file = META_COOKIE_FILE if is_meta_source(url) and os.path.isfile(META_COOKIE_FILE) else COOKIE_FILE
    if os.path.isfile(cookie_file):
        options["cookiefile"] = cookie_file
    runtimes = {}
    for runtime in ("deno", "node"):
        executable = shutil.which(runtime)
        if executable:
            runtimes[runtime] = {"path": executable}
    if runtimes:
        options["js_runtimes"] = runtimes
    if is_tiktok(url) and TIKTOK_PROXY:
        options["proxy"] = TIKTOK_PROXY
    options.update(overrides)
    return options


def tikwm_info(url):
    # Third-party resolver: send only the public TikTok URL, never account cookies.
    endpoint = "https://www.tikwm.com/api/?" + urlencode({"url": url})
    req = Request(endpoint, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(req, timeout=20) as response:
        payload = json.loads(response.read(2 * 1024 * 1024))
    data = payload.get("data") or {}
    if payload.get("code") != 0 or not data.get("play"):
        raise ValueError("TikTok resolver: " + str(payload.get("msg") or "No public video was returned."))
    media_url = urljoin("https://www.tikwm.com", data["play"])
    check_url(media_url)
    author = data.get("author") or {}
    return {
        "id": str(data.get("id") or uuid.uuid4().hex[:12]),
        "title": data.get("title") or "TikTok video", "duration": data.get("duration") or 0,
        "thumbnail": urljoin("https://www.tikwm.com", data.get("cover") or ""),
        "uploader": author.get("nickname") or author.get("unique_id") or "TikTok",
        "webpage_url": url, "_resolver": "tikwm",
        "formats": [{"url": media_url, "ext": "mp4", "protocol": "https",
                     "vcodec": "h264", "acodec": "aac",
                     "http_headers": {"User-Agent": "Mozilla/5.0"}}],
    }


def media_info(url, refresh=False):
    with lock:
        cached = metadata_cache.get(url)
        if not refresh and cached and cached[0] > time.time():
            return copy.deepcopy(cached[1])
    check_url(url)
    resolver_error = None
    # Avoid a known regional short-link redirect before trying the alternative route.
    if is_tiktok(url) and TIKTOK_RESOLVER == "tikwm" and not TIKTOK_PROXY:
        try:
            info = tikwm_info(url)
        except Exception as exc:
            resolver_error = str(exc)
            info = None
    else:
        info = None
    if info is None:
        try:
            with yt_dlp.YoutubeDL(ydl_options(url, skip_download=True, ignore_no_formats_error=True)) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info or info.get("_type") in {"playlist", "multi_video"}:
                    raise ValueError("Use a single video link, not a playlist or profile.")
                for item in info.get("formats") or []:
                    headers = dict(item.get("http_headers") or info.get("http_headers") or {})
                    cookie = ydl.cookiejar.get_cookie_header(item.get("url", ""))
                    if cookie:
                        headers["Cookie"] = cookie
                    item["http_headers"] = headers
        except Exception as exc:
            if resolver_error:
                raise ValueError("TikTok could not be loaded. " + resolver_error
                                 + " Native TikTok access also failed from this server.") from exc
            raise
    if not info.get("formats"):
        raise ValueError("No playable formats were returned for this video.")
    with lock:
        metadata_cache[url] = (time.time() + 300, copy.deepcopy(info))
        # Bound caches on a public long-running service.
        for key, value in list(metadata_cache.items()):
            if value[0] < time.time():
                metadata_cache.pop(key, None)
    return info


def basic_info(info, url):
    return {"title": info.get("title") or "Video", "duration": info.get("duration") or 0,
            "thumbnail": info.get("thumbnail"), "uploader": info.get("uploader") or "",
            "url": url}


def safe_name(title):
    name = "".join(c for c in (title or "velaur_export") if c.isalnum() or c in " _-").strip()
    return name[:140] or "velaur_export"


def run_ffmpeg(job_id, args):
    save_job(job_id, stage="Converting media", percent=None)
    stderr_path = JOBS_DIR / job_id / "ffmpeg.log"
    with stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args],
                                stdout=subprocess.DEVNULL, stderr=stderr)
        try:
            deadline = time.monotonic() + 7200
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    raise subprocess.TimeoutExpired(proc.args, 7200)
                with accounts.tx() as connection:
                    accounts.get_user(connection, jobs[job_id]["_owner"])
                time.sleep(2)
            code = proc.returncode
        except BaseException:
            proc.kill()
            proc.wait()
            raise
    if code != 0:
        log.error("FFmpeg failed for job %s: %s", job_id, stderr_path.read_text(errors="replace")[-1500:])
        raise ValueError("Media conversion failed. Try a different video or a shorter clip.")


def probe_video(path):
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,height",
                           "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
    if proc.returncode:
        raise ValueError("Downloaded media could not be read.")
    return json.loads(proc.stdout)


def trim_arguments(clip):
    if clip is None:
        return []
    start, end = clip
    args = ["-ss", str(start)]
    if end is not None:
        args += ["-t", str(end - start)]
    return args


def make_mp4(job_id, source, target, height, clip=None, quality="high", preview=False):
    probe = probe_video(source)
    video = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None:
        raise ValueError("This source contains no video track. Choose MP3.")
    can_copy = clip is None and video.get("codec_name") == "h264" and (video.get("height") or 0) <= height
    args = trim_arguments(clip) + ["-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-sn"]
    if can_copy:
        args += ["-c:v", "copy"]
    else:
        args += ["-vf", f"scale=-2:trunc(min({height}\\,ih)/2)*2",
                 "-c:v", "libx264", "-preset", "ultrafast" if preview else "veryfast",
                 "-crf", "26" if preview else {"max": "18", "high": "21", "standard": "25"}.get(quality, "21"),
                 "-pix_fmt", "yuv420p"]
    args += ["-c:a", "copy" if audio and audio.get("codec_name") == "aac" else "aac",
             "-movflags", "+faststart", str(target)]
    run_ffmpeg(job_id, args)


def is_meta_source(url):
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain)
               for domain in ("instagram.com", "facebook.com", "fb.watch", "fb.com"))


def download_source(job_id, url, info, height=1080, audio=False, clip=None):
    directory = JOBS_DIR / job_id
    prepared = info.get("_prepared_source") if is_instagram_source(url) else None
    if prepared:
        source = Path(prepared)
        if source.resolve().parent != directory.resolve() or not source.is_file():
            raise ValueError("Verified source does not belong to this job.")
        return source, False
    fresh_meta = is_meta_source(url)
    last_update = [0]
    def progress(event):
        now = time.monotonic()
        if now - last_update[0] < 0.6 and event.get("status") != "finished":
            return
        last_update[0] = now
        total = event.get("total_bytes") or event.get("total_bytes_estimate") or 0
        downloaded = event.get("downloaded_bytes") or 0
        save_job(job_id, stage="Downloading source" if event.get("status") != "finished" else "Preparing media",
                 percent=round(min(100, downloaded / total * 100), 1) if total else None,
                 speed=event.get("speed"), eta=event.get("eta"))
    save_job(job_id, stage="Downloading source", percent=None)
    if info.get("_resolver") == "tikwm":
        source = directory / "source.mp4"
        fmt = info["formats"][0]
        req = Request(fmt["url"], headers=fmt.get("http_headers") or {})
        with urlopen(req, timeout=25) as response, source.open("wb") as output:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                progress({"status": "downloading", "total_bytes": total, "downloaded_bytes": downloaded})
        return source, False
    preferred = "bestaudio/best" if audio else (
        f"bv*[height<={height}][vcodec^=avc1]+ba[acodec^=mp4a]/"
        f"b[height<={height}][ext=mp4]/bv*[height<={height}]+ba/"
        f"b[height<={height}]/b"
    )
    if fresh_meta:
        # Prefer separate video/audio like the native CLI before falling back to
        # progressive media. Downscale locally if no lower-resolution DASH exists.
        preferred = "bestaudio/best" if audio else (
            f"bv*[height<={height}]+ba/bv*+ba/b[height<={height}]/b")
    if is_instagram_source(url):
        h = max(1080, height)
        preferred = "bestaudio/best" if audio else f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    youtube_audio = audio and (
        host == "youtu.be" or host == "youtube.com"
        or host.endswith(".youtube.com")
    )
    if youtube_audio:
        # youtube-audio-combined-1
        preferred = "b[ext=mp4]/bv*+ba/b"
    options = ydl_options(url, format=preferred, outtmpl=str(directory / "source.%(ext)s"),
                          merge_output_format="mp4", progress_hooks=[progress],
                          postprocessor_hooks=[lambda e: save_job(job_id, stage="Merging media", percent=None)],
                          overwrites=True)
    # Download only the chosen clip when formats are suitable for FFmpeg range downloading.
    if clip and not audio and not fresh_meta:
        start, end = clip
        options["force_keyframes_at_cuts"] = True
        options["download_ranges"] = download_range_func(None, [(start, end if end is not None else float("inf"))])
    if fresh_meta:
        def verify_fresh_access(fresh, *, incomplete=False):
            if incomplete:
                return None
            # Extraction and media download use one cookie jar/header context.
            # Recheck duration/quota against this fresh metadata before download.
            duration = float(fresh.get("duration") or 0)
            if jobs[job_id]["kind"] == "preview":
                accounts.reserve_duration(jobs[job_id]["_owner"], job_id, duration, None)
            else:
                reserve_export_duration(job_id, duration, clip)
            return None
        options["match_filter"] = verify_fresh_access
        save_job(job_id, stage="Refreshing source access", percent=None)
    with yt_dlp.YoutubeDL(options) as ydl:
        if fresh_meta or youtube_audio:
            if not ydl.extract_info(url, download=True):
                raise ValueError("This source could not be downloaded.")
        else:
            # Keep the existing YouTube/TikTok metadata reuse path.
            ydl.process_ie_result(copy.deepcopy(info), download=True)
    sources = [p for p in directory.glob("source.*")
               if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".ogg", ".opus", ".mov"}]
    if not sources:
        raise ValueError("The source download did not produce a media file.")
    # A merged source is preferred; never select a separate .fXXX video/audio track.
    merged = [p for p in sources if len(p.name.split(".")) == 2]
    return max(merged or sources, key=lambda p: p.stat().st_mtime), bool(clip and not audio and not fresh_meta)


def source_cache_key(owner, url):
    return hashlib.sha256((owner + "\0" + url).encode()).hexdigest()


def cleanup_source_cache():
    now = time.time()
    with lock:
        expired = [(key, value) for key, value in source_cache.items()
                   if value.get("expires", 0) <= now or not Path(value.get("path", "")).is_file()]
        for key, _ in expired:
            source_cache.pop(key, None)
    for _, value in expired:
        path = Path(value.get("path", ""))
        try:
            if path.resolve().is_relative_to(SOURCE_CACHE_DIR.resolve()):
                shutil.rmtree(path.parent, ignore_errors=True)
        except (OSError, ValueError):
            pass


def register_cached_source(owner, url, source, info):
    """Keep one private source briefly so a later export avoids a second download."""
    cleanup_source_cache()
    source = Path(source)
    if not source.is_file() or source.stat().st_size <= 0:
        return None
    key = (owner, url)
    directory = SOURCE_CACHE_DIR / source_cache_key(owner, url)
    temporary = directory.with_name(directory.name + ".tmp-" + uuid.uuid4().hex[:8])
    temporary.mkdir(parents=True)
    target = temporary / ("source" + (source.suffix.lower() or ".mp4"))
    try:
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)
        details = probe_video(target)
        video = next((item for item in details.get("streams", []) if item.get("codec_type") == "video"), {})
        audio = next((item for item in details.get("streams", []) if item.get("codec_type") == "audio"), None)
        available = max([int(item.get("height") or 0) for item in info.get("formats", [])
                         if item.get("vcodec") not in {None, "none"}] or [int(video.get("height") or 0)])
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
        os.replace(temporary, directory)
        target = directory / target.name
        record = {"path": str(target), "expires": time.time() + SOURCE_CACHE_TTL,
                  "height": int(video.get("height") or 0), "available_height": available,
                  "audio": bool(audio), "owner": owner, "url": url}
        with lock:
            old = source_cache.get(key)
            source_cache[key] = record
        if old and old.get("path") != str(target):
            old_path = Path(old.get("path", ""))
            try:
                if old_path.resolve().is_relative_to(SOURCE_CACHE_DIR.resolve()):
                    shutil.rmtree(old_path.parent, ignore_errors=True)
            except (OSError, ValueError):
                pass
        return record
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def claim_cached_source(job_id, url, height, audio=False):
    owner = jobs[job_id]["_owner"]
    key = (owner, url)
    with lock:
        pending = source_fetches.get(key)
    if pending and not pending.is_set():
        save_job(job_id, stage="Downloading source", percent=None)
        pending.wait(timeout=3)
        if not pending.is_set():
            return None
    cleanup_source_cache()
    with lock:
        record = copy.deepcopy(source_cache.get(key))
    if not record or record["owner"] != owner or record["url"] != url:
        return None
    if audio and not record.get("audio"):
        return None
    needed = min(int(height), int(record.get("available_height") or height))
    if not audio and int(record.get("height") or 0) < needed:
        return None
    source = Path(record["path"])
    if not source.is_file():
        return None
    destination = JOBS_DIR / job_id / ("cached-source" + source.suffix.lower())
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination, False


def prefetch_source(owner, url, info, height):
    """Download privately after Preview is ready; never changes the visible preview job."""
    key = (owner, url)
    with lock:
        event = source_fetches.get(key)
        if event is None:
            event = threading.Event()
            source_fetches[key] = event
        elif event.is_set():
            return
    directory = SOURCE_CACHE_DIR / (source_cache_key(owner, url) + ".fetch-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    try:
        # Give the preview relay first access to bandwidth before warming export data.
        time.sleep(1.5)
        with accounts.tx() as connection:
            user = accounts.get_user(connection, owner)
            access = accounts.access(connection, user)
        if not access["enabled"]:
            return
        limit = access["limits"]["upload_gb"] * 1000 ** 3
        received = [0]
        def bounded(event_data):
            received[0] = max(received[0], int(event_data.get("downloaded_bytes") or 0))
            if received[0] > limit:
                raise ValueError("Prepared source exceeds the account file-size limit.")
        if info.get("_resolver") == "tikwm":
            source = directory / "source.mp4"
            fmt = info["formats"][0]
            with urlopen(Request(fmt["url"], headers=fmt.get("http_headers") or {}), timeout=25) as response, source.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    received[0] += len(chunk)
                    if received[0] > limit:
                        raise ValueError("Prepared source exceeds the account file-size limit.")
        else:
            preferred = (f"bv*[height<={height}][vcodec^=avc1]+ba[acodec^=mp4a]/"
                         f"b[height<={height}][ext=mp4]/bv*[height<={height}]+ba/"
                         f"b[height<={height}]/b")
            options = ydl_options(url, format=preferred, outtmpl=str(directory / "source.%(ext)s"),
                                  merge_output_format="mp4", progress_hooks=[bounded], overwrites=True)
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.process_ie_result(copy.deepcopy(info), download=True)
            candidates = [item for item in directory.glob("source.*") if item.is_file()
                          and item.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
            merged = [item for item in candidates if len(item.name.split(".")) == 2]
            if not candidates:
                return
            source = max(merged or candidates, key=lambda item: item.stat().st_mtime)
        if source.stat().st_size > limit:
            return
        record = register_cached_source(owner, url, source, info)
        if record:
            record_path = Path(record["path"])
            if record_path.parent != directory:
                shutil.rmtree(directory, ignore_errors=True)
    except Exception:
        log.warning("Background source preparation failed for %s", url, exc_info=True)
        shutil.rmtree(directory, ignore_errors=True)
    finally:
        with lock:
            source_fetches.pop(key, None)
        event.set()


def schedule_source_prefetch(owner, url, info, height):
    if is_meta_source(url):
        return
    cleanup_source_cache()
    key = (owner, url)
    with lock:
        existing = source_cache.get(key)
        if existing and existing.get("expires", 0) > time.time() and Path(existing.get("path", "")).is_file():
            return
        if key in source_fetches:
            return
        source_fetches[key] = threading.Event()
    prefetch_pool.submit(prefetch_source, owner, url, copy.deepcopy(info), height)


def instagram_duration_info(job_id, request):
    """Verify a bounded local source when Instagram omits duration metadata."""
    url = request['url']
    info = media_info(url)
    if not is_instagram_source(url):
        return info
    try:
        known = float(info.get('duration') or 0)
    except (ValueError, TypeError):
        known = 0
    if __import__('math').isfinite(known) and known > 0:
        return info
    owner = jobs[job_id]['_owner']
    with accounts.tx() as connection:
        user = accounts.get_user(connection, owner)
        access = accounts.access(connection, user)
    if not access['enabled']:
        raise ValueError('Your access is no longer active.')
    if jobs[job_id]['kind'] == 'export' and request.get('output_format', 'mp4') != 'mp3' and resolution_height(request.get('resolution')) > access['limits']['height']:
        raise ValueError('This resolution is not included in your plan.')
    # Preparation is bounded before duration is known. It never produces a
    # downloadable result until FFprobe and the normal quota checks succeed.
    budget = min(access['limits']['upload_gb'] * 1000**3, 128 * 1024**2)
    deadline = time.monotonic() + 120
    received = {}
    def bounded_progress(event):
        key = str(event.get('filename') or 'source')
        received[key] = max(received.get(key, 0), int(event.get('downloaded_bytes') or 0))
        if sum(received.values()) > budget:
            raise ValueError('Duration verification exceeds its 128 MB preparation limit.')
        if time.monotonic() > deadline:
            raise ValueError('Source duration verification timed out. Please retry.')
        if event.get('status') in {'downloading', 'finished'}:
            save_job(job_id, stage='Downloading source to verify duration', percent=None)
    directory = JOBS_DIR / job_id
    options = ydl_options(url,
        format='bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        outtmpl=str(directory / 'verified-source.%(ext)s'),
        merge_output_format='mp4', max_filesize=budget,
        progress_hooks=[bounded_progress], overwrites=True)
    save_job(job_id, stage='Verifying source duration', percent=None)
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            fresh = downloader.extract_info(url, download=True)
        if time.monotonic() > deadline:
            raise ValueError('Source duration verification timed out. Please retry.')
        if not fresh:
            raise ValueError('Instagram did not return a downloadable source.')
        candidates = [p for p in directory.glob('verified-source.*')
            if p.is_file() and p.suffix.lower() in {'.mp4', '.mkv', '.webm', '.mov'}
            and len(p.name.split('.')) == 2]
        if not candidates:
            raise ValueError('Duration verification produced no complete file; source may exceed its size limit.')
        source = max(candidates, key=lambda p: p.stat().st_mtime)
        if source.stat().st_size > budget:
            raise ValueError('Duration verification exceeds its preparation size limit.')
        save_job(job_id, stage='Checking actual video duration', percent=None)
        probe = probe_video(source)
        duration = float(probe.get('format', {}).get('duration') or 0)
        if jobs[job_id]['kind'] == 'preview':
            accounts.reserve_duration(owner, job_id, duration, None)
        else:
            clip = clip_range(request.get('start_time'), request.get('end_time'), duration)
            reserve_export_duration(job_id, duration, clip)
        info['duration'] = duration
        if fresh.get('title'):
            info['title'] = fresh['title']
        # This path is only passed inside the owning job; never cached/shared.
        info['_prepared_source'] = str(source)
        return info
    except BaseException:
        for partial in directory.glob('verified-source.*'):
            if partial.is_file():
                partial.unlink(missing_ok=True)
        raise



def run_preview(job_id, request):
    url = request["url"]
    info = instagram_duration_info(job_id, request)
    accounts.reserve_duration(jobs[job_id]["_owner"], job_id, float(info.get("duration") or 0), None)
    summary = basic_info(info, url)
    save_job(job_id, media=summary, stage="Preparing preview")
    direct = [f for f in info.get("formats", [])
              if f.get("url") and f.get("protocol") in {"http", "https"}
              and not f.get("manifest_url") and "manifest.googlevideo.com" not in f["url"]
              and f.get("vcodec") not in {None, "none"} and f.get("acodec") not in {None, "none"}
              and f.get("ext") == "mp4" and (f.get("vcodec", "").startswith(("avc", "h264")))]
    if direct and not request.get("force_download") and not is_instagram_source(url):
        small = [f for f in direct if (f.get("height") or 0) <= 480]
        fmt = max(small or direct, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0))
        token = uuid.uuid4().hex
        with lock:
            streams[token] = {"expires": time.time() + 600, "url": fmt["url"],
                              "headers": fmt.get("http_headers") or info.get("http_headers") or {}, "_owner": jobs[job_id]["_owner"]}
            for key in [k for k, v in streams.items() if v["expires"] < time.time()]:
                streams.pop(key, None)
        result = dict(summary, stream_url=f"/api/stream/{token}", preview_mode="stream")
    else:
        source, _ = download_source(job_id, url, info, height=480)
        target = JOBS_DIR / job_id / "preview.mp4"
        make_mp4(job_id, source, target, 480, preview=True)
        try:
            register_cached_source(jobs[job_id]["_owner"], url, source, info)
        except Exception:
            log.warning("Could not retain preview source for a later export", exc_info=True)
        source.unlink(missing_ok=True)
        save_job(job_id, _file=str(target))
        result = dict(summary, stream_url=f"/api/files/{job_id}?preview=true", preview_mode="file")
    save_job(job_id, state="done", stage="Preview ready", percent=100, result=result)


def reserve_export_duration(job_id, duration, clip):
    duration = float(duration or 0)
    length = duration if clip is None else (min(clip[1], duration) if clip[1] is not None else duration) - clip[0]
    accounts.reserve_duration(jobs[job_id]["_owner"], job_id, duration, length)


def run_export(job_id, request):
    is_upload = bool(request.get("_upload"))
    info = None if is_upload else instagram_duration_info(job_id, request)
    title = request.get("_title") if is_upload else info.get("title")
    duration = None if is_upload else info.get("duration")
    clip = clip_range(request.get("start_time"), request.get("end_time"), duration)
    output_format = request.get("output_format", "mp4")
    height = resolution_height(request.get("resolution"))
    with accounts.tx() as connection:
        user = accounts.get_user(connection, jobs[job_id]["_owner"])
        maximum = accounts.access(connection, user)["limits"]["height"]
    if output_format != "mp3" and height > maximum:
        raise ValueError("This resolution is not included in your plan.")
    if is_upload:
        source = Path(request["_upload"])
        probe = probe_video(source)
        duration = float(probe.get("format", {}).get("duration") or 0)
        clip = clip_range(request.get("start_time"), request.get("end_time"), duration)
        clipped = False
        reserve_export_duration(job_id, duration, clip)
    else:
        reserve_export_duration(job_id, duration, clip)
        cached = claim_cached_source(job_id, request["url"], height, output_format == "mp3")
        try:
            source, clipped = cached or download_source(job_id, request["url"], info, height, output_format == "mp3", clip)
        except Exception:
            # Signed source URLs can expire. Re-extract once, then let the error surface.
            with lock:
                metadata_cache.pop(request["url"], None)
            info = media_info(request["url"], refresh=True)
            source, clipped = download_source(job_id, request["url"], info, height, output_format == "mp3", clip)
    target = JOBS_DIR / job_id / ("export." + output_format)
    if output_format == "mp3":
        bitrate = {"high": "320k", "standard": "192k", "low": "128k"}.get(request.get("quality"), "192k")
        run_ffmpeg(job_id, trim_arguments(clip) + ["-i", str(source), "-vn", "-c:a", "libmp3lame", "-b:a", bitrate, str(target)])
    else:
        make_mp4(job_id, source, target, height, None if clipped else clip, request.get("quality", "high"))
    if not target.exists() or target.stat().st_size == 0:
        raise ValueError("The export produced an empty file.")
    filename = safe_name(title) + "." + output_format
    save_job(job_id, state="done", stage="File ready", percent=100, _file=str(target),
             result={"download_url": f"/api/files/{job_id}", "filename": filename, "size": target.stat().st_size})
    source.unlink(missing_ok=True)


def execute(job_id, request):
    try:
        with accounts.tx(True) as connection:
            connection.execute("UPDATE media_usage SET state='running',updated=? WHERE id=? AND state='queued'",(time.time(),job_id))
        save_job(job_id, state="running", stage="Reading video information", percent=None)
        (run_preview if jobs[job_id]["kind"] == "preview" else run_export)(job_id, request)
    except Exception as exc:
        failed_stage = jobs.get(job_id, {}).get("stage")
        message = str(exc).replace("\x1b", "")[-1600:]
        try:
            accounts.finish(job_id, "error")
        except Exception:
            log.error("Could not release usage for interrupted job %s", job_id)
        log.exception("Job %s failed", job_id)
        save_job(job_id, state="error", stage="Could not process media", error=message, failed_stage=failed_stage, percent=None)
    finally:
        # Failed uploads and temporary cookie-bearing metadata stay off the static surface.
        if request.get("_upload"):
            Path(request["_upload"]).unlink(missing_ok=True)


def new_job(kind, request):
    owner = request.pop("_owner", None)
    if not owner:
        raise HTTPException(401, "Sign in with Google to continue.")
    with lock:
        for old_id, old_job in list(jobs.items()):
            if old_job["state"] in {"done", "error"} and time.time() - old_job.get("updated", old_job["created"]) > 86400:
                shutil.rmtree(JOBS_DIR / old_id, ignore_errors=True)
                jobs.pop(old_id, None)
        if sum(j["state"] in {"queued", "running"} for j in jobs.values()) >= 16:
            raise HTTPException(429, "The server queue is busy. Please retry shortly.")
        if kind == "preview":
            key = (owner, request["url"], bool(request.get("force_download")))
            previous = preview_cache.get(key)
            if previous:
                job = jobs.get(previous)
                if job and job["state"] == "done" and time.time() - job["created"] < 240:
                    with accounts.tx() as connection:
                        if not accounts.access(connection, accounts.get_user(connection, owner))["enabled"]:
                            raise HTTPException(403, "Your access has ended.")
                    return public_job(job)
        job_id = uuid.uuid4().hex
        accounts.reserve(owner, kind, job_id, output_format=request.get("output_format", "mp4"))
        try:
            (JOBS_DIR / job_id).mkdir()
            jobs[job_id] = {"id": job_id, "_owner": owner, "_source_url": request.get("url", ""), "kind": kind, "state": "queued",
                           "stage": "Waiting for a processing slot", "percent": None, "created": time.time()}
            save_job(job_id)
            if kind == "preview":
                preview_cache[key] = job_id
            pool.submit(execute, job_id, request)
        except Exception:
            accounts.finish(job_id, "error")
            jobs.pop(job_id, None)
            shutil.rmtree(JOBS_DIR / job_id, ignore_errors=True)
            raise
        return public_job(jobs[job_id])


class MediaRequest(BaseModel):
    url: str
    output_format: str = "mp4"
    resolution: str = "1080"
    quality: str = "high"
    start_time: str | None = None
    end_time: str | None = None
    force_download: bool = False


@app.get("/")
@app.head("/")
@app.get("/index.html")
@app.head("/index.html")
def index():
    return FileResponse(BASE / "index.html", headers={"Cache-Control": "no-cache"})




@app.get("/pricing")
@app.head("/pricing")
def pricing_page():
    return FileResponse(BASE / "pricing.html", headers={"Cache-Control": "no-cache"})


@app.get("/robots.txt", include_in_schema=False)
def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /downloads/\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return PlainTextResponse(body, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE_URL}/</loc></url>\n"
        f"  <url><loc>{SITE_URL}/pricing</loc></url>\n"
        f"  <url><loc>{SITE_URL}/privacy</loc></url>\n"
        f"  <url><loc>{SITE_URL}/terms</loc></url>\n"
        "</urlset>\n"
    )
    return Response(body, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/share-preview-v33.jpg", include_in_schema=False)
@app.head("/share-preview-v33.jpg", include_in_schema=False)
def share_preview(request: WebRequest):
    return FileResponse(
        BASE / "share-preview-v33.jpg", media_type="image/jpeg", method=request.method,
        headers={"Cache-Control": "public, max-age=86400",
                 "X-Content-Type-Options": "nosniff"},
    )


@app.get("/favicon.ico")
def favicon():
    return FileResponse(BASE / "favicon-v32.png")


@app.get("/static/{asset}")
@app.head("/static/{asset}")
def asset_file(asset: str, request: WebRequest):
    # Do not mount /app as a public directory: it also holds cookies and source code.
    if Path(asset).name != asset or Path(asset).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".css", ".js"}:
        raise HTTPException(404)
    path = BASE / asset
    if not path.is_file():
        raise HTTPException(404)
    media_types = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".svg": "image/svg+xml", ".ico": "image/x-icon",
        ".css": "text/css", ".js": "text/javascript",
    }
    return FileResponse(path, media_type=media_types[path.suffix.lower()],
                        method=request.method,
                        headers={"Cache-Control": "no-cache" if path.suffix.lower() in {".js", ".css"} else "public, max-age=86400"})


@app.get("/api/health")
def health():
    return {"status": "ok", "admin_patch": "user-controls-1", "audio_patch": "mp3-plan-fix-1", "version": "4.0", "ui_version": "4.0.3", "media_patch": "instagram-duration-1", "performance_patch": "source-cache-1.1",
            "share_image": (BASE / "share-preview-v33.jpg").is_file(), "ffmpeg": bool(shutil.which("ffmpeg")),
            "ffprobe": bool(shutil.which("ffprobe")), "tiktok_resolver": TIKTOK_RESOLVER}


@app.post("/api/jobs/preview", status_code=202)
def preview(request: MediaRequest, web: WebRequest):
    return new_job("preview", dict(request.dict(), _owner=web.state.user["id"]))


@app.post("/api/jobs/export", status_code=202)
def export(request: MediaRequest, web: WebRequest):
    if request.output_format not in {"mp4", "mp3"}:
        raise HTTPException(400, "Choose MP4 or MP3.")
    return new_job("export", dict(request.dict(), _owner=web.state.user["id"]))


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, request: WebRequest):
    accounts.require_owner(request.state.user["id"], job_id)
    with lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "This job was not found. Start it again.")
        return public_job(job)


@app.get("/api/files/{job_id}")
@app.head("/api/files/{job_id}")
def job_file(job_id: str, request: WebRequest, preview: bool = False):
    accounts.require_owner(request.state.user["id"], job_id)
    with lock:
        job = copy.deepcopy(jobs.get(job_id))
    if not job or job.get("state") != "done" or not job.get("_file"):
        raise HTTPException(404, "The file is not ready.")
    if time.time() - job.get("updated", job["created"]) > 86400:
        raise HTTPException(410, "This export has expired. Prepare it again.")
    path = Path(job["_file"])
    if not path.is_file():
        raise HTTPException(410, "This file is no longer available. Export it again.")
    size = path.stat().st_size
    start, end, status = 0, size - 1, 200
    requested_range = request.headers.get("range")
    if requested_range:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested_range.strip())
        if not match or not any(match.groups()):
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        else:
            start = max(0, size - int(last))
        if start > end or start >= size:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        status = 206
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1),
               "Cache-Control": "private, max-age=300"}
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    if not preview:
        filename = job.get("result", {}).get("filename") or path.name
        headers["Content-Disposition"] = "attachment; filename*=UTF-8''" + quote(filename)
    mime = "audio/mpeg" if path.suffix == ".mp3" else "video/mp4"
    if not preview and request.method == "GET" and start == 0:
        try:
            from admin_tools import record_download_request
            record_download_request(request.state.user["id"], job_id)
        except Exception:
            log.warning("Could not record download request for %s", job_id)
    if request.method == "HEAD":
        return Response(status_code=status, headers=headers, media_type=mime)
    def chunks():
        with path.open("rb") as source:
            source.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = source.read(min(256 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
            if not preview and remaining == 0 and start == 0 and end == size - 1:
                try:
                    from admin_tools import record_download_complete
                    record_download_complete(request.state.user["id"], job_id, size)
                except Exception:
                    log.warning("Could not record completed file transfer for %s", job_id)
    return StreamingResponse(chunks(), status_code=status, headers=headers, media_type=mime)


@app.get("/api/stream/{token}")
def relay(token: str, request: WebRequest):
    with lock:
        stream = copy.deepcopy(streams.get(token))
    if not stream or stream.get("_owner") != request.state.user["id"] or stream["expires"] < time.time():
        raise HTTPException(410, "Preview expired. Load it again.")
    headers = {k: v for k, v in stream["headers"].items()
               if k.lower() not in {"host", "content-length", "connection", "accept-encoding"}}
    headers["Accept-Encoding"] = "identity"
    if request.headers.get("range"):
        headers["Range"] = request.headers["range"]
    try:
        upstream = urlopen(Request(stream["url"], headers=headers), timeout=20)
    except HTTPError as exc:
        status = exc.code if exc.code in {403, 404, 410, 416} else 502
        raise HTTPException(status, "Video source rejected preview. Use compatible preview.") from exc
    except OSError as exc:
        raise HTTPException(502, "Video source could not be reached.") from exc
    passed = {k: v for k, v in upstream.headers.items()
              if k.lower() in {"content-length", "content-range", "accept-ranges"}}
    passed["Cache-Control"] = "private, no-store"
    def chunks():
        try:
            while True:
                chunk = upstream.read(128 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()
    return StreamingResponse(chunks(), status_code=upstream.status, headers=passed, media_type="video/mp4")


@app.post("/api/upload-export", status_code=202)
async def upload_export(request: WebRequest, file: UploadFile = File(...), output_format: str = Form("mp4"),
                        resolution: str = Form("1080"), quality: str = Form("high"),
                        start_time: str | None = Form(None), end_time: str | None = Form(None)):
    if output_format not in {"mp3", "mp4"}:
        raise HTTPException(400, "Choose MP4 or MP3.")
    extension = Path(file.filename or "upload.mp4").suffix.lower()
    if extension not in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
        raise HTTPException(400, "Choose a supported video file.")
    with accounts.tx() as connection:
        user = accounts.get_user(connection, request.state.user["id"])
        maximum_upload = accounts.access(connection, user)["limits"]["upload_gb"] * 1000 ** 3
    source = JOBS_DIR / ("upload_" + uuid.uuid4().hex + extension)
    try:
        size = 0
        with source.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > maximum_upload:
                    raise HTTPException(413, "This upload exceeds your plan's file-size limit.")
                output.write(chunk)
        if not size:
            raise HTTPException(400, "The uploaded file is empty.")
        return new_job("export", {"_owner": request.state.user["id"], "_upload": str(source), "_title": Path(file.filename).stem,
                                 "output_format": output_format, "resolution": resolution, "quality": quality,
                                 "start_time": start_time, "end_time": end_time})
    except Exception:
        source.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.get("/privacy", include_in_schema=False)
def privacy_page():
    return FileResponse(BASE / "privacy.html")


@app.get("/terms", include_in_schema=False)
def terms_page():
    return FileResponse(BASE / "terms.html")

# activity-outcomes-2
