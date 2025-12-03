#!/usr/bin/env python3
import os
import time
import random
import socket
import threading
import subprocess
from pathlib import Path
from typing import List, Optional

# -------------------------------------------------------
#  LOFI STREAMER v8.7.1 — H264 Baseline + Classic Viz + YouTube Timestamp Fix
#  Changes vs v8.7:
#    * Removed unsupported ffmpeg flag: -video_track_timescale
#    * Pipeline now uses stable: -use_wallclock_as_timestamps 1 + -fflags +genpts
#    * Prevents ffmpeg from exiting, allows YouTube to receive video
# -------------------------------------------------------

VERSION = "8.7.1"

OUTPUT_W = 1280
OUTPUT_H = 720

LOGO_PADDING = 40
TEXT_PADDING = 40
VIZ_HEIGHT = 120

CAM_FIFO = Path("/tmp/camfifo.ts")
AUDIO_FIFO = Path("/tmp/lofi_audio.pcm")
NOWPLAYING_FILE = Path("/tmp/nowplaying.txt")

CHOSEN_FPS: Optional[int] = None
GOP_SIZE: Optional[int] = None

# Picamera2
try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except:
    PSUTIL_AVAILABLE = False

# ---------------- BASE DIR ----------------

def _detect_base_dir() -> Path:
    base = Path(__file__).resolve().parent
    return base.parent if base.name.lower() == "servers" else base

BASE_DIR = _detect_base_dir()

# ---------------- ENV HELPERS ----------------

def _env_path(name: str, default: Path) -> Path:
    raw = Path(os.environ.get(name, str(default))).expanduser()
    try:
        return raw.resolve(strict=False)
    except:
        return raw

def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except:
        return default

def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}

PLAYLIST_DIR = _env_path("LOFI_PLAYLIST_DIR", BASE_DIR / "Sounds")
LOGO_DIR = _env_path("LOFI_BRAND_DIR", BASE_DIR / "Logo")

STREAM_URL_FILE = _env_path("LOFI_STREAM_URL_FILE", BASE_DIR / "stream_url.txt")
STREAM_URL_ENV = os.environ.get("LOFI_YOUTUBE_URL", "")

FFMPEG_LOGO = _env_path("LOFI_BRAND_IMAGE", LOGO_DIR / "TestLogo200.png")

FALLBACK_FPS = _env_int("LOFI_FALLBACK_FPS", 25)

CHECK_HOST = os.environ.get("LOFI_CHECK_HOST", "a.rtmp.youtube.com")
CHECK_PORT = _env_int("LOFI_CHECK_PORT", 1935)

SKIP_NETWORK_CHECK = _env_bool("LOFI_SKIP_NETWORK_CHECK")

# ---------------- NETWORK CHECK ----------------

def check_network() -> bool:
    try:
        with socket.create_connection((CHECK_HOST, CHECK_PORT), timeout=3):
            return True
    except:
        return False

# ---------------- PI READY ----------------

def wait_for_pi_ready():
    print("⏳ Waiting for Pi to be fully ready...")

    while os.system("ping -c1 1.1.1.1 >/dev/null 2>&1") != 0:
        print("⏳ Waiting for network…")
        time.sleep(2)
    print("🌐 Internet OK")

    while True:
        try:
            socket.gethostbyname("google.com")
            print("🔍 DNS OK")
            break
        except:
            print("⏳ Waiting for DNS…")
            time.sleep(1)

    while True:
        try:
            yr = int(subprocess.check_output(["date", "+%Y"]))
        except:
            yr = 1970
        if yr >= 2023:
            print("⏱ Time synced")
            break
        print("⏳ Waiting for NTP…")
        time.sleep(1)

    print("✅ Pi Ready!\n")

# ---------------- FPS ----------------

def detect_pi_model():
    try:
        with open("/proc/device-tree/model") as f:
            m = f.read().lower()
            if "raspberry pi 5" in m: return 5
            if "raspberry pi 4" in m: return 4
    except:
        pass
    return 0

def choose_fps():
    model = detect_pi_model()
    if model == 5:
        base = 30
    elif model == 4:
        base = 25
    else:
        base = FALLBACK_FPS

    if PSUTIL_AVAILABLE:
        load = psutil.cpu_percent(interval=1.0)
        print(f"🧠 Startup CPU load: {load:.1f}%")
        if load > 85:
            return 20

    print(f"🎞 Auto-selected FPS: {base}")
    return base

# ---------------- TRACKS ----------------

def load_stream_url():
    if STREAM_URL_ENV:
        return STREAM_URL_ENV
    if STREAM_URL_FILE.exists():
        print(f"📄 Loaded RTMP URL from {STREAM_URL_FILE}")
        return STREAM_URL_FILE.read_text().strip()
    print("❌ Missing RTMP URL")
    return ""

def _is_valid_audio(t: Path):
    n = t.name.lower()
    if n.startswith("._") or n.startswith("."):
        return False
    return t.suffix.lower() in [".mp3", ".wav", ".flac", ".m4a"]

def load_tracks() -> List[Path]:
    tracks = [t for t in PLAYLIST_DIR.iterdir() if _is_valid_audio(t)]
    print(f"🎶 Loaded {len(tracks)} tracks.")
    return tracks

def _playlist_iterator(tracks):
    while True:
        lst = list(tracks)
        random.shuffle(lst)
        for t in lst:
            yield t

# ---------------- NOW PLAYING ----------------

def _escape(s: str):
    return s.replace(":", r"\:")

def get_nowplaying(t: Path):
    try:
        import mutagen
        m = mutagen.File(t, easy=True)
        title = m.get("title", [""])[0]
        artist = m.get("artist", [""])[0]
        if not title:
            title = t.stem
    except:
        title = t.stem
        artist = ""
    return _escape(f"{artist} - {title}" if artist else title)

def write_nowplaying(txt):
    NOWPLAYING_FILE.write_text(f"Now Playing: {txt}")

# ---------------- CLASSIC BAR VISUALISER ----------------

def _build_filter_chain(video_ref: str) -> str:
    """
    Compact bar visualiser (200px × 24px),
    aligned perfectly with Now Playing text on the right.
    """

    viz_w = 200     # width as requested
    viz_h = 24      # EXACT same height as the Now Playing text (fontsize=24)

    np_file = str(NOWPLAYING_FILE)

    # Match the vertical position of the Now Playing text
    text_y = OUTPUT_H - viz_h - 10   # 10px margin above bottom
    viz_y = text_y                   # align both exactly

    viz_x = 40   # small left margin

    # Classic Lofi bar visualiser but compact
    viz = (
        f"[1:a]showfreqs=mode=bar:"
        f"ascale=log:colors=0xCCCCCC:"
        f"size={viz_w}x{viz_h}[viz];"
    )

    logo_x = f"W-w-{LOGO_PADDING}"
    logo_y = LOGO_PADDING

    if FFMPEG_LOGO.exists():
        return (
            viz +
            f"{video_ref}scale={OUTPUT_W}:{OUTPUT_H},format=yuv420p[v0];"
            f"[v0][2:v]overlay={logo_x}:{logo_y}[v1];"
            f"[v1][viz]overlay={viz_x}:{viz_y}[v2];"
            f"[v2]drawtext=textfile='{np_file}':reload=1:"
            f"fontcolor=white:fontsize=24:"
            f"x=w-tw-{TEXT_PADDING}:y={text_y}[vout]"
        )

    else:
        return (
            viz +
            f"{video_ref}scale={OUTPUT_W}:{OUTPUT_H},format=yuv420p[v0];"
            f"[v0][viz]overlay={viz_x}:{viz_y}[v1];"
            f"[v1]drawtext=textfile='{np_file}':reload=1:"
            f"fontcolor=white:fontsize=24:"
            f"x=w-tw-{TEXT_PADDING}:y={text_y}[vout]"
        )

# ---------------- CAMERA ----------------

def start_camera():
    if not PICAMERA2_AVAILABLE:
        print("❌ Picamera2 not installed.")
        return None

    fps = CHOSEN_FPS

    print("📸 Initialising Picamera2…")
    picam = Picamera2()

    config = picam.create_video_configuration(
        main={"format": "YUV420", "size": (OUTPUT_W, OUTPUT_H)},
        controls={"FrameRate": fps}
    )
    picam.configure(config)

    encoder = H264Encoder(bitrate=1800000)
    out = FileOutput(str(CAM_FIFO))

    try:
        picam.start_recording(encoder, out)
    except Exception as e:
        print("❌ Failed to start camera:", e)
        return None

    print(f"📸 Picamera2 (H264 Baseline {fps}fps) → {CAM_FIFO}")
    return picam

def stop_camera(picam):
    if not picam: return
    print("📷 Stopping Picamera2…")
    try: picam.stop_recording()
    except: pass
    try: picam.close()
    except: pass

# ---------------- AUDIO FEEDER ----------------

def audio_feeder(tracks, stop_event):
    print("🎚 Audio feeder started.")
    with open(AUDIO_FIFO, "wb", buffering=0) as fd:
        for t in _playlist_iterator(tracks):
            if stop_event.is_set(): break

            np = get_nowplaying(t)
            print(f"🎧 {np}")
            write_nowplaying(np)

            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-re", "-vn", "-i", str(t),
                "-f", "s16le", "-ar", "44100", "-ac", "2",
                "pipe:1"
            ]
            p = subprocess.Popen(cmd, stdout=fd)

            while p.poll() is None and not stop_event.is_set():
                time.sleep(0.5)

            if stop_event.is_set():
                try: p.terminate()
                except: pass
                break

    print("🎚 Audio feeder stopped.")

# ---------------- FFMPEG PIPELINE ----------------

def start_pipeline(stream_url: str):
    print("🎥 Starting ffmpeg pipeline…")

    g = GOP_SIZE

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",

        # Timestamp stabilisation (YouTube safe)
        "-fflags", "+genpts",
        "-use_wallclock_as_timestamps", "1",

        # Video input
        "-thread_queue_size", "512",
        "-f", "h264", "-i", str(CAM_FIFO),

        # Audio input
        "-thread_queue_size", "512",
        "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", str(AUDIO_FIFO),
    ]

    if FFMPEG_LOGO.exists():
        cmd += ["-loop", "1", "-i", str(FFMPEG_LOGO)]

    filter_chain = _build_filter_chain("[0:v]")

    cmd += [
        "-filter_complex", filter_chain,
        "-map", "[vout]", "-map", "1:a",

        "-c:v", "libx264",
        "-profile:v", "baseline",
        "-level", "3.1",

        "-preset", "ultrafast",
        "-b:v", "1800k",
        "-maxrate", "1800k",
        "-bufsize", "2400k",

        "-g", str(g),
        "-keyint_min", str(g),
        "-sc_threshold", "0",

        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",

        "-f", "flv", stream_url
    ]

    return subprocess.Popen(cmd)

# ---------------- MAIN ----------------

def main():
    global CHOSEN_FPS, GOP_SIZE

    print(f"🌙 LOFI STREAMER v{VERSION} — H264 Baseline + YouTube Fix\n")

    wait_for_pi_ready()

    stream_url = load_stream_url()
    if not stream_url:
        return

    tracks = load_tracks()
    if not tracks:
        return

    CHOSEN_FPS = choose_fps()
    GOP_SIZE = CHOSEN_FPS * 4
    print(f"🎞 Final FPS: {CHOSEN_FPS}, GOP: {GOP_SIZE}")

    if not SKIP_NETWORK_CHECK and not check_network():
        print("⚠️ RTMP host not reachable.")

    for f in (CAM_FIFO, AUDIO_FIFO):
        if f.exists(): os.unlink(f)
        os.mkfifo(f)
        print(f"✓ FIFO ready: {f}")

    write_nowplaying("Initialising…")

    stop_event = threading.Event()

    ff = start_pipeline(stream_url)

    picam = start_camera()
    if not picam:
        ff.terminate()
        return

    audio_thread = threading.Thread(
        target=audio_feeder, args=(tracks, stop_event), daemon=True
    )
    audio_thread.start()

    try:
        while True:
            if ff.poll() is not None:
                print("❌ ffmpeg exited.")
                break

            if PSUTIL_AVAILABLE:
                print(f"🧠 CPU {psutil.cpu_percent():.1f}%")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("👋 Stopping streamer...")

    finally:
        stop_event.set()
        try: ff.terminate()
        except: pass

        stop_camera(picam)

        try: audio_thread.join(timeout=3)
        except: pass

        print("👋 Streamer shut down.")

if __name__ == "__main__":
    main()
