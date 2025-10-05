# server.py
# FastAPI streaming server that controls an ffmpeg subprocess and broadcasts audio to multiple listener clients.
# NOTES:
# - Requires ffmpeg installed on the host.
# - Configure the FFMPEG_CMD in the config.json or environment; default is for Linux PulseAudio ("default").
# - This server exposes control endpoints that the Telegram bot will call to start/stop stream and update metadata.
# - /stream serves the live audio to multiple listeners.
from fastapi import FastAPI, Response, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
import asyncio, subprocess, threading, time, os, json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULT_CONFIG = {
    "ffmpeg_cmd": ["ffmpeg", "-f", "pulse", "-i", "default", "-vn", "-acodec", "libmp3lame", "-b:a", "128k", "-f", "mp3", "pipe:1"],
    "host": "0.0.0.0",
    "port": 8000,
    "player_path": "/player.html"
}

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH,"r") as f:
        cfg = json.load(f)
else:
    cfg = DEFAULT_CONFIG
    with open(CONFIG_PATH,"w") as f:
        json.dump(cfg, f, indent=2)

app = FastAPI()

# broadcaster state
_ffmpeg_proc = None
_read_task = None
_subscribers = set()
_metadata = {"song": "DJ is offline"}
_lock = threading.Lock()

async def _broadcaster_loop(proc):
    """
    Read from ffmpeg stdout and broadcast chunks to all subscriber queues.
    """
    try:
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                await asyncio.sleep(0.01)
                continue
            dead = []
            for q in list(_subscribers):
                try:
                    # put_nowait so the reader can drop if slow
                    q.put_nowait(chunk)
                except asyncio.QueueFull:
                    # if queue is full, drop to avoid blocking
                    pass
    except Exception as e:
        print("broadcaster loop error:", e)
    finally:
        # close subscriber queues
        for q in list(_subscribers):
            try:
                q.put_nowait(b"")
            except:
                pass

def start_ffmpeg():
    global _ffmpeg_proc, _read_task
    with _lock:
        if _ffmpeg_proc is not None and _ffmpeg_proc.poll() is None:
            return False, "Already running"
        cmd = cfg.get("ffmpeg_cmd", DEFAULT_CONFIG["ffmpeg_cmd"])
        print("Starting ffmpeg with:", cmd)
        # Start subprocess
        _ffmpeg_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        # Start reader in a background asyncio task via thread
        loop = asyncio.get_event_loop()
        _read_task = loop.create_task(_broadcaster_loop(_ffmpeg_proc))
        return True, "Started"

def stop_ffmpeg():
    global _ffmpeg_proc, _read_task
    with _lock:
        if _ffmpeg_proc is None:
            return False, "Not running"
        try:
            _ffmpeg_proc.kill()
        except:
            pass
        _ffmpeg_proc = None
        if _read_task:
            _read_task.cancel()
            _read_task = None
        return True, "Stopped"

@app.post("/control/start")
async def control_start():
    ok, msg = start_ffmpeg()
    if not ok:
        return JSONResponse({"ok": False, "msg": msg})
    return {"ok": True, "msg": msg}

@app.post("/control/stop")
async def control_stop():
    ok, msg = stop_ffmpeg()
    return {"ok": ok, "msg": msg}

@app.post("/metadata")
async def set_metadata(payload: dict):
    global _metadata
    song = payload.get("song")
    if song:
        _metadata["song"] = song
    return {"ok": True, "metadata": _metadata}

@app.get("/metadata")
async def get_metadata():
    return _metadata

@app.get("/player.html")
async def player_file():
    path = os.path.join(os.path.dirname(__file__), "player.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Player not found")
    return FileResponse(path, media_type="text/html")

@app.get("/stream")
async def stream():
    """
    Client connects here to receive raw mp3 stream. Each client gets its own asyncio.Queue which receives
    copies of chunks pushed by the broadcaster loop.
    """
    if _ffmpeg_proc is None or _ffmpeg_proc.poll() is not None:
        raise HTTPException(status_code=503, detail="Stream is not running")
    q = asyncio.Queue(maxsize=256)
    _subscribers.add(q)

    async def generator():
        try:
            while True:
                chunk = await q.get()
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                _subscribers.discard(q)
            except:
                pass
    headers = {"Content-Type": "audio/mpeg"}
    return StreamingResponse(generator(), headers=headers)
