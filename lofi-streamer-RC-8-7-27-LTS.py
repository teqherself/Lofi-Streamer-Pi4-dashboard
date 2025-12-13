#!/usr/bin/env python3
"""
LOFI STREAMER v8.7.27 — WOOBOT LTS (FIXED)

✔ Continuous FFmpeg pipeline
✔ Picamera2 stays running
✔ Audio FIFO never closes
✔ Playlist reshuffles forever
✔ Safe Python clock + date
✔ Single drawtext
✔ Logo overlay (picam.png) — FIXED INPUT
✔ macOS junk ignored
✔ No restart on track change
"""

import os
import sys
import time
import socket
import random
import signal
import threading
import subprocess
from pathlib import Path
from datetime import datetime

VERSION = "8.7.27-woobot-lts"

BASE_DIR = Path(__file__).resolve().parent.parent
SOUNDS_DIR = BASE_DIR / "Sounds"
LOGO_FILE = BASE_DIR / "Logo" / "picam.png"
STREAM_URL_FILE = BASE_DIR / "stream_url.txt"

CAM_FIFO = Path("/tmp/camfifo.ts")
AUDIO_FIFO = Path("/tmp/lofi_audio.pcm")
OVERLAY_FILE = Path("/tmp/overlay.txt")

WIDTH, HEIGHT = 1280, 720
FPS = 20
GOP = FPS * 4

VIDEO_BITRATE = "1500k"
VIDEO_MAXRATE = "1800k"
VIDEO_BUFSIZE = "2400k"
AUDIO_BITRATE = "128k"

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

GLOBAL_STOP = threading.Event()
SESSION_STOP = threading.Event()
NOW_PLAYING = "Starting…"


# --------------------------------------------------
def log(msg):
    print(msg, flush=True)


# --------------------------------------------------
def wait_for_pi_ready():
    log("⏳ Waiting for Pi to be fully ready...")

    while os.system("ping -c1 1.1.1.1 >/dev/null 2>&1") != 0:
        time.sleep(2)
    log("🌐 Internet OK")

    while True:
        try:
            socket.gethostbyname("google.com")
            break
        except OSError:
            time.sleep(1)
    log("🔍 DNS OK")

    while True:
        try:
            if int(subprocess.check_output(["date", "+%Y"])) >= 2023:
                break
        except Exception:
            pass
        time.sleep(1)
    log("⏱ Time synced")
    log("✅ Pi Ready!\n")


# --------------------------------------------------
def valid_track(p: Path) -> bool:
    return (
        p.suffix.lower() == ".mp3"
        and not p.name.startswith(("._", "."))
        and p.stat().st_size > 100_000
    )


def load_tracks():
    tracks = [p for p in SOUNDS_DIR.iterdir() if valid_track(p)]
    if not tracks:
        log("❌ No valid tracks found")
        sys.exit(1)
    random.shuffle(tracks)
    log(f"🎶 Loaded {len(tracks)} tracks (filtered). Shuffled.")
    return tracks


def playlist_forever(stop_event):
    while not stop_event.is_set():
        tracks = load_tracks()
        for t in tracks:
            if stop_event.is_set():
                return
            yield t


# --------------------------------------------------
def overlay_writer():
    while not GLOBAL_STOP.is_set():
        try:
            OVERLAY_FILE.write_text(
                f"{datetime.now():%Y-%m-%d %H:%M}\n{NOW_PLAYING}"
            )
        except Exception:
            pass
        time.sleep(1)


# --------------------------------------------------
def audio_feeder(stop_event):
    global NOW_PLAYING
    log("🎚 Audio feeder started (continuous FIFO)")

    silence = b"\x00\x00" * 44100 * 2

    while not GLOBAL_STOP.is_set() and not stop_event.is_set():
        try:
            with open(AUDIO_FIFO, "wb", buffering=0) as fifo:
                for track in playlist_forever(stop_event):
                    NOW_PLAYING = track.stem
                    log(f"🎧 {NOW_PLAYING}")

                    cmd = [
                        "ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-re", "-vn", "-i", str(track),
                        "-f", "s16le", "-ar", "44100", "-ac", "2",
                        "pipe:1"
                    ]

                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)

                    while True:
                        chunk = p.stdout.read(4096)
                        if not chunk:
                            break
                        fifo.write(chunk)

                    p.wait()
                    fifo.write(silence)

        except BrokenPipeError:
            log("⚠️ Audio FIFO broken pipe — reopening")
            time.sleep(1)

    log("🎚 Audio feeder stopped")


# --------------------------------------------------
def start_camera():
    code = f"""
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import time

p = Picamera2()
cfg = p.create_video_configuration(
    main={{"size": ({WIDTH},{HEIGHT}), "format": "YUV420"}},
    controls={{"FrameRate": {FPS}}}
)
p.configure(cfg)

enc = H264Encoder(
    bitrate={int(VIDEO_BITRATE[:-1])*1000},
    profile="baseline",
    iperiod={GOP},
    repeat=True
)

p.start_recording(enc, FileOutput("{CAM_FIFO}"))
while True:
    time.sleep(1)
"""
    subprocess.Popen(["python3", "-u", "-c", code])
    log("📸 Picamera2 running")


# --------------------------------------------------
def start_ffmpeg(stream_url):
    subprocess.Popen([
        "ffmpeg",
        "-loglevel", "warning",
        "-fflags", "+genpts",
        "-use_wallclock_as_timestamps", "1",

        "-thread_queue_size", "4096",
        "-f", "h264", "-i", str(CAM_FIFO),

        "-thread_queue_size", "4096",
        "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", str(AUDIO_FIFO),

        "-loop", "1", "-i", str(LOGO_FILE),

        "-filter_complex",
        f"[0:v]scale={WIDTH}:{HEIGHT},format=yuv420p[v];"
        f"[v][2:v]overlay=W-w-40:40[v2];"
        f"[v2]drawtext=fontfile={FONT}:"
        f"textfile='{OVERLAY_FILE}':reload=1:"
        f"x=40:y=40:fontsize=24:fontcolor=white:borderw=2[vout]",

        "-map", "[vout]",
        "-map", "1:a",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-profile:v", "baseline",
        "-b:v", VIDEO_BITRATE,
        "-maxrate", VIDEO_MAXRATE,
        "-bufsize", VIDEO_BUFSIZE,
        "-g", str(GOP),

        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,

        "-f", "flv",
        stream_url
    ])
    log("🎥 FFmpeg streaming")


# --------------------------------------------------
def shutdown(*_):
    GLOBAL_STOP.set()
    SESSION_STOP.set()
    subprocess.call(["pkill", "-9", "ffmpeg"])
    subprocess.call(["pkill", "-9", "-f", "picamera"])
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


# --------------------------------------------------
def main():
    log(f"🌙 LOFI STREAMER {VERSION}\n")
    wait_for_pi_ready()

    stream_url = STREAM_URL_FILE.read_text().strip()

    for f in (CAM_FIFO, AUDIO_FIFO):
        if f.exists():
            f.unlink()
        os.mkfifo(f)
        log(f"✓ FIFO ready: {f}")

    threading.Thread(target=overlay_writer, daemon=True).start()
    threading.Thread(target=audio_feeder, args=(SESSION_STOP,), daemon=True).start()

    start_camera()
    time.sleep(2)
    start_ffmpeg(stream_url)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
