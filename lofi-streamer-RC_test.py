#!/usr/bin/env python3
import os
import time
import random
import socket
import threading
import subprocess
from pathlib import Path
from typing import List, Optional
import signal
import sys

# ======================================================================
#  LOFI STREAMER v8.7.11 — PI4 BROADCAST STABLE (Susan fix)
# ======================================================================
# Fixes vs v8.7.10:
#  ✔ Audio feeder NEVER permanently exits (reopens FIFO, resumes playlist)
#  ✔ Removes non-blocking FIFO hack (prevents long-run timing drift)
#  ✔ Prevents FFmpeg PIPE deadlocks (no stdout pipe; stderr drained by reader)
#  ✔ Watchdog detects "stalled but alive" FFmpeg via -progress heartbeat
#  ✔ Optional scheduled clean restart (default 6h) for true 24/7 stability
#  ✔ Safer, ordered cleanup + restart loop
# ======================================================================

VERSION = "8.7.11-woobot-broadcast"

OUTPUT_W = 1280
OUTPUT_H = 720

LOGO_PADDING = 40
TEXT_PADDING = 40

CAM_FIFO = Path("/tmp/camfifo.ts")
AUDIO_FIFO = Path("/tmp/lofi_audio.pcm")

NOWPLAYING_FILE = Path("/tmp/nowplaying.txt")
CURRENT_TRACK_FILE = Path("/tmp/current_track.txt")

# Watchdog / stability
WATCHDOG_INTERVAL = 10            # seconds
STALL_TIMEOUT = 120               # if no ffmpeg progress for this long => restart
MAX_RESTART_ATTEMPTS = 6
RESTART_COOLDOWN = 60             # seconds

# Optional scheduled clean restart (strongly recommended for Pi4)
SESSION_MAX_SECONDS = int(os.environ.get("LOFI_SESSION_MAX_SECONDS", str(6 * 3600)))  # default 6h (0 disables)

CHOSEN_FPS: Optional[int] = None
GOP_SIZE: Optional[int] = None

VIDEO_BITRATE = "1500k"
VIDEO_MAXRATE = "1800k"
VIDEO_BUFSIZE = "2400k"

# -------------------------------------------------------
# Picamera2 Imports
# -------------------------------------------------------
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
except Exception:
    PSUTIL_AVAILABLE = False


# -------------------------------------------------------
# BASE DIR DISCOVERY
# -------------------------------------------------------
def _detect_base_dir() -> Path:
    base = Path(__file__).resolve().parent
    return base.parent if base.name.lower() == "servers" else base


BASE_DIR = _detect_base_dir()


# -------------------------------------------------------
# ENV HELPERS
# -------------------------------------------------------
def _env_path(name: str, default: Path) -> Path:
    raw = Path(os.environ.get(name, str(default))).expanduser()
    try:
        return raw.resolve(strict=False)
    except Exception:
        return raw


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


# -------------------------------------------------------
# DIRS / CONFIG
# -------------------------------------------------------
PLAYLIST_DIR = _env_path("LOFI_PLAYLIST_DIR", BASE_DIR / "Sounds")
LOGO_DIR = _env_path("LOFI_BRAND_DIR", BASE_DIR / "Logo")

STREAM_URL_FILE = _env_path("LOFI_STREAM_URL_FILE", BASE_DIR / "stream_url.txt")
STREAM_URL_ENV = os.environ.get("LOFI_YOUTUBE_URL", "")

FFMPEG_LOGO = _env_path("LOFI_BRAND_IMAGE", LOGO_DIR / "picam.png")

FALLBACK_FPS = _env_int("LOFI_FALLBACK_FPS", 20)

CHECK_HOST = os.environ.get("LOFI_CHECK_HOST", "a.rtmp.youtube.com")
CHECK_PORT = _env_int("LOFI_CHECK_PORT", 1935)

SKIP_NETWORK_CHECK = _env_bool("LOFI_SKIP_NETWORK_CHECK", False)
AUTO_RESTART = _env_bool("LOFI_AUTO_RESTART", True)


# -------------------------------------------------------
# NETWORK CHECK
# -------------------------------------------------------
def check_network() -> bool:
    try:
        with socket.create_connection((CHECK_HOST, CHECK_PORT), timeout=3):
            return True
    except OSError:
        return False


# -------------------------------------------------------
# PI READY
# -------------------------------------------------------
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
        except OSError:
            print("⏳ Waiting for DNS…")
            time.sleep(1)

    while True:
        try:
            yr = int(subprocess.check_output(["date", "+%Y"]))
        except Exception:
            yr = 1970
        if yr >= 2023:
            print("⏱ Time synced")
            break
        print("⏳ Waiting for NTP…")
        time.sleep(1)

    print("✅ Pi Ready!\n")


# -------------------------------------------------------
# PI MODEL + PARAM SELECTION
# -------------------------------------------------------
def detect_pi_model():
    try:
        with open("/proc/device-tree/model") as f:
            m = f.read().lower()
            if "raspberry pi 5" in m:
                return 5
            if "raspberry pi 4" in m:
                return 4
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return 0


def choose_stream_params():
    model = detect_pi_model()

    fps = FALLBACK_FPS
    bitrate = "1500k"
    maxrate = "1800k"
    bufsize = "2400k"

    if model == 5:
        fps = 30
        bitrate = "2500k"
        maxrate = "3000k"
        bufsize = "4000k"
    elif model == 4:
        fps = 20
        bitrate = "1500k"
        maxrate = "1800k"
        bufsize = "2400k"

    if PSUTIL_AVAILABLE:
        load = psutil.cpu_percent(interval=1.0)
        print(f"🧠 Startup CPU load: {load:.1f}%")
        if load > 85:
            print("⚠️ High startup CPU — tuning safer parameters")
            fps = max(15, fps - 5)

    print(f"🎞 Auto-selected FPS: {fps}")
    print(f"📺 Video bitrate: {bitrate}, maxrate: {maxrate}, bufsize: {bufsize}")
    return fps, bitrate, maxrate, bufsize


# -------------------------------------------------------
# TRACK HANDLING
# -------------------------------------------------------
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
    if not PLAYLIST_DIR.exists():
        print(f"❌ Playlist directory missing: {PLAYLIST_DIR}")
        try:
            PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
            print("📁 Created playlist directory. Add audio files to start streaming.")
        except Exception as e:
            print(f"❌ Failed to create playlist directory: {e}")
            return []

    if not PLAYLIST_DIR.is_dir():
        print(f"❌ Playlist path is not a directory: {PLAYLIST_DIR}")
        return []

    try:
        tracks = [t for t in PLAYLIST_DIR.iterdir() if _is_valid_audio(t)]
    except Exception as e:
        print(f"❌ Failed to read playlist directory: {e}")
        return []

    print(f"🎶 Loaded {len(tracks)} tracks.")
    return tracks


def _playlist_iterator(stop_event: threading.Event):
    while not stop_event.is_set():
        tracks = load_tracks()
        if not tracks:
            print("⚠️ No tracks found. Waiting 10 seconds before retry...")
            for _ in range(10):
                if stop_event.is_set():
                    return
                time.sleep(1)
            continue

        lst = list(tracks)
        random.shuffle(lst)
        for t in lst:
            if stop_event.is_set():
                return
            yield t


# -------------------------------------------------------
# NOW PLAYING
# -------------------------------------------------------
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
    except Exception:
        title = t.stem
        artist = ""

    return _escape(f"{artist} - {title}" if artist else title)


def write_nowplaying(txt: str):
    try:
        NOWPLAYING_FILE.write_text(f"Now Playing: {txt}")
    except Exception:
        pass
    try:
        CURRENT_TRACK_FILE.write_text(txt)
    except Exception:
        pass


# -------------------------------------------------------
# FILTER CHAIN
# -------------------------------------------------------
def _build_filter_chain(video_ref: str) -> str:
    viz_w = 140
    viz_h = 28

    np_file = str(NOWPLAYING_FILE)

    text_y = OUTPUT_H - viz_h - 30
    viz_y = text_y
    viz_x = 40

    timestamp = (
        f"drawtext=text='%{{localtime}}':"
        f"x={LOGO_PADDING}:y={LOGO_PADDING}:"
        "fontsize=24:fontcolor=white:borderw=2"
    )

    viz = (
        f"[1:a]showfreqs=mode=bar:ascale=log:colors=0xCCCCCC:"
        f"size={viz_w}x{viz_h}[viz];"
    )

    logo_x = f"W-w-{LOGO_PADDING}"
    logo_y = LOGO_PADDING

    if FFMPEG_LOGO.exists():
        return (
            viz +
            f"{video_ref}scale={OUTPUT_W}:{OUTPUT_H},format=yuv420p[v0];"
            f"[v0]{timestamp}[v1];"
            f"[v1][2:v]overlay={logo_x}:{logo_y}[v2];"
            f"[v2][viz]overlay={viz_x}:{viz_y}[v3];"
            f"[v3]drawtext=textfile='{np_file}':reload=1:fontcolor=white:"
            f"fontsize=24:x=w-tw-{TEXT_PADDING}:y={text_y}[vout]"
        )

    return (
        viz +
        f"{video_ref}scale={OUTPUT_W}:{OUTPUT_H},format=yuv420p[v0];"
        f"[v0]{timestamp}[v1];"
        f"[v1][viz]overlay={viz_x}:{viz_y}[v2];"
        f"[v2]drawtext=textfile='{np_file}':reload=1:fontcolor=white:"
        f"fontsize=24:x=w-tw-{TEXT_PADDING}:y={text_y}[vout]"
    )


# -------------------------------------------------------
# CAMERA (stable blocking FIFO output)
# -------------------------------------------------------
def start_camera():
    if not PICAMERA2_AVAILABLE:
        print("❌ Picamera2 not installed.")
        return None

    fps = CHOSEN_FPS or 20

    print("📸 Initialising Picamera2…")
    picam = Picamera2()

    config = picam.create_video_configuration(
        main={"format": "YUV420", "size": (OUTPUT_W, OUTPUT_H)},
        controls={"FrameRate": fps}
    )
    picam.configure(config)

    def _br_to_int(br: str) -> int:
        if br.endswith("k"):
            return int(br[:-1]) * 1000
        return int(br)

    encoder = H264Encoder(bitrate=_br_to_int(VIDEO_BITRATE))

    # IMPORTANT: blocking FIFO output is more stable for long runtimes
    out = FileOutput(str(CAM_FIFO))

    try:
        picam.start_recording(encoder, out)
    except Exception as e:
        print("❌ Failed to start camera:", e)
        return None

    print(f"📸 Picamera2 (H264 Baseline {fps}fps, {VIDEO_BITRATE}) → {CAM_FIFO}")
    return picam


def stop_camera(picam):
    if not picam:
        return
    print("📷 Stopping Picamera2…")
    try:
        picam.stop_recording()
    except Exception:
        pass
    try:
        picam.close()
    except Exception:
        pass


# -------------------------------------------------------
# AUDIO FEEDER (self-healing)
# -------------------------------------------------------
def audio_feeder(stop_event: threading.Event):
    print("🎚 Audio feeder started.")

    while not stop_event.is_set():
        # Open FIFO (blocks until ffmpeg opens for reading)
        try:
            with open(AUDIO_FIFO, "wb", buffering=0) as fd:
                for t in _playlist_iterator(stop_event):
                    if stop_event.is_set():
                        break

                    np = get_nowplaying(t)
                    print(f"🎧 {np}")
                    write_nowplaying(np)

                    cmd = [
                        "ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-re", "-vn", "-i", str(t),
                        "-f", "s16le", "-ar", "44100", "-ac", "2", "pipe:1"
                    ]

                    # Send decoded PCM directly into the FIFO
                    try:
                        p = subprocess.Popen(
                            cmd,
                            stdout=fd,
                            stderr=subprocess.DEVNULL,  # avoid PIPE fill deadlocks
                        )

                        while p.poll() is None and not stop_event.is_set():
                            time.sleep(0.5)

                        if stop_event.is_set():
                            try:
                                p.terminate()
                                p.wait(timeout=2)
                            except Exception:
                                try:
                                    p.kill()
                                except Exception:
                                    pass
                            break

                        # If decode fails, move to next track
                        if p.returncode != 0:
                            print(f"⚠️ Audio decode error for {t.name} (ffmpeg rc={p.returncode})")
                            continue

                    except BrokenPipeError:
                        # FFmpeg stopped reading audio FIFO. Do NOT exit permanently.
                        print("⚠️ Audio FIFO broken pipe — FFmpeg likely restarted/stalled. Reopening FIFO...")
                        time.sleep(1)
                        break
                    except Exception as e:
                        print(f"❌ Audio feeder error: {e}")
                        time.sleep(1)
                        continue

        except FileNotFoundError:
            # FIFO not created yet, wait
            time.sleep(0.5)
        except Exception as e:
            if stop_event.is_set():
                break
            print(f"❌ Audio feeder open/write error: {e}")
            time.sleep(1)

    print("🎚 Audio feeder stopped.")


# -------------------------------------------------------
# FFMPEG PIPELINE (with progress heartbeat)
# -------------------------------------------------------
def start_pipeline(stream_url: str):
    print("🎥 Starting ffmpeg pipeline…")

    g = GOP_SIZE or 80

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-fflags", "+genpts+discardcorrupt",
        "-flags", "low_delay",
        "-thread_queue_size", "4096",
        "-probesize", "64k",
        "-analyzeduration", "0",
        "-vsync", "1",
        "-use_wallclock_as_timestamps", "1",

        # Inputs
        "-f", "h264", "-i", str(CAM_FIFO),
        "-thread_queue_size", "4096",
        "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", str(AUDIO_FIFO),
    ]

    if FFMPEG_LOGO.exists():
        cmd += ["-loop", "1", "-i", str(FFMPEG_LOGO)]

    filter_chain = _build_filter_chain("[0:v]")

    cmd += [
        "-filter_complex", filter_chain,
        "-map", "[vout]", "-map", "1:a",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-profile:v", "baseline",
        "-level", "3.1",
        "-b:v", VIDEO_BITRATE,
        "-maxrate", VIDEO_MAXRATE,
        "-bufsize", VIDEO_BUFSIZE,
        "-g", str(g),
        "-keyint_min", str(g),
        "-sc_threshold", "0",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",

        # Heartbeat: emits key=value progress regularly to stderr
        "-progress", "pipe:2",

        "-f", "flv", stream_url,
    ]

    # IMPORTANT: do not PIPE stdout (can deadlock). stderr is drained by a reader thread.
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1)


# -------------------------------------------------------
# FFmpeg stderr/progress reader (prevents pipe deadlocks + gives heartbeat)
# -------------------------------------------------------
class FFmpegTelemetry:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_progress_ts = time.time()
        self.last_line_ts = time.time()
        self.last_error_line = ""
        self.seen_broken_pipe = False

    def update_line(self, line: str):
        now = time.time()
        with self.lock:
            self.last_line_ts = now

            # -progress emits key=value lines including out_time_ms periodically
            if line.startswith("out_time_ms=") or line.startswith("frame=") or line.startswith("progress="):
                self.last_progress_ts = now

            low = line.lower()
            if "broken pipe" in low or "av_interleaved_write_frame" in low:
                self.seen_broken_pipe = True
                self.last_error_line = line.strip()
            elif "error" in low or "failed" in low or "connection" in low:
                self.last_error_line = line.strip()

    def snapshot(self):
        with self.lock:
            return (self.last_progress_ts, self.last_line_ts, self.last_error_line, self.seen_broken_pipe)


def ffmpeg_reader_thread(ff: subprocess.Popen, tel: FFmpegTelemetry, stop_event: threading.Event):
    try:
        if not ff.stderr:
            return
        for line in ff.stderr:
            if stop_event.is_set():
                break
            line = line.strip()
            if not line:
                continue
            tel.update_line(line)
            # Print only useful bits (avoid spam)
            if "broken pipe" in line.lower():
                print(f"⚠️ FFmpeg: {line}")
            elif "error" in line.lower() or "failed" in line.lower():
                print(f"⚠️ FFmpeg: {line}")
    except Exception:
        pass


# -------------------------------------------------------
# WATCHDOG (monitors FFmpeg health and stalls)
# -------------------------------------------------------
def watchdog_monitor(ff: subprocess.Popen, tel: FFmpegTelemetry, stop_event: threading.Event, restart_flag):
    print("🐕 Watchdog started")
    started = time.time()
    last_net_check = 0.0

    while not stop_event.is_set():
        time.sleep(WATCHDOG_INTERVAL)
        if stop_event.is_set():
            break

        # scheduled clean restart
        if SESSION_MAX_SECONDS > 0 and (time.time() - started) > SESSION_MAX_SECONDS:
            print(f"🔁 Scheduled restart after {SESSION_MAX_SECONDS}s (broadcast hygiene)")
            restart_flag["do_restart"] = True
            stop_event.set()
            break

        # process died
        if ff.poll() is not None:
            print("❌ Watchdog: FFmpeg process exited")
            restart_flag["do_restart"] = True
            stop_event.set()
            break

        last_progress_ts, _, last_err, seen_bp = tel.snapshot()

        # stalled but alive (common RTMP dead socket case)
        if (time.time() - last_progress_ts) > STALL_TIMEOUT:
            print(f"❌ Watchdog: FFmpeg stalled (no progress for {STALL_TIMEOUT}s). Restarting.")
            if last_err:
                print(f"   Last FFmpeg note: {last_err}")
            restart_flag["do_restart"] = True
            stop_event.set()
            break

        # broken pipe seen
        if seen_bp:
            print("❌ Watchdog: FFmpeg reported broken pipe. Restarting.")
            if last_err:
                print(f"   FFmpeg: {last_err}")
            restart_flag["do_restart"] = True
            stop_event.set()
            break

        # light network checks every 5 minutes
        if time.time() - last_net_check > 300:
            last_net_check = time.time()
            if not check_network():
                print("⚠️ Watchdog: RTMP host unreachable (network issue).")

        # optional CPU warning
        if PSUTIL_AVAILABLE:
            try:
                cpu = psutil.cpu_percent(interval=0.2)
                if cpu > 95:
                    print(f"⚠️ Watchdog: High CPU usage ({cpu:.1f}%)")
            except Exception:
                pass

    print("🐕 Watchdog stopped")


# -------------------------------------------------------
# MAIN LOOP with AUTO-RESTART
# -------------------------------------------------------
class StreamerState:
    def __init__(self):
        self.restart_count = 0
        self.last_restart_time = 0.0
        self.stop_event = threading.Event()
        self.global_stop = False


def cleanup_resources(ff, picam, audio_thread, reader_thread, stop_event: threading.Event):
    print("🧹 Cleaning up resources...")

    stop_event.set()

    # Stop camera first (stops writing to FIFO)
    stop_camera(picam)

    # Stop FFmpeg
    if ff and ff.poll() is None:
        try:
            ff.terminate()
            ff.wait(timeout=5)
        except Exception:
            try:
                ff.kill()
            except Exception:
                pass

    # Join threads
    if audio_thread and audio_thread.is_alive():
        try:
            audio_thread.join(timeout=3)
        except Exception:
            pass

    if reader_thread and reader_thread.is_alive():
        try:
            reader_thread.join(timeout=2)
        except Exception:
            pass

    # Best effort close stderr to stop reader
    try:
        if ff and ff.stderr:
            ff.stderr.close()
    except Exception:
        pass


def run_streaming_session(state: StreamerState, stream_url: str) -> bool:
    state.stop_event.clear()

    # Create FIFOs fresh
    for f in (CAM_FIFO, AUDIO_FIFO):
        if f.exists():
            try:
                os.unlink(f)
            except Exception:
                pass
        try:
            os.mkfifo(f)
            print(f"✓ FIFO ready: {f}")
        except Exception as e:
            print(f"❌ Failed to create FIFO {f}: {e}")
            return False

    write_nowplaying("Initialising…")

    # Start FFmpeg first (becomes FIFO reader)
    ff = start_pipeline(stream_url)
    if not ff:
        print("❌ Failed to start FFmpeg")
        return False

    tel = FFmpegTelemetry()
    reader = threading.Thread(target=ffmpeg_reader_thread, args=(ff, tel, state.stop_event), daemon=True)
    reader.start()

    # Start camera (FIFO writer)
    picam = start_camera()
    if not picam:
        print("❌ Failed to start camera")
        cleanup_resources(ff, None, None, reader, state.stop_event)
        return False

    # Start audio feeder (FIFO writer) — self healing
    audio_thread = threading.Thread(target=audio_feeder, args=(state.stop_event,), daemon=True)
    audio_thread.start()

    restart_flag = {"do_restart": False}

    # Start watchdog
    wd = threading.Thread(
        target=watchdog_monitor,
        args=(ff, tel, state.stop_event, restart_flag),
        daemon=True
    )
    wd.start()

    # Session monitor loop
    try:
        while not state.stop_event.is_set() and not state.global_stop:
            if ff.poll() is not None:
                print("❌ FFmpeg exited")
                restart_flag["do_restart"] = True
                state.stop_event.set()
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("👋 Stopping streamer (Ctrl+C)...")
        state.global_stop = True
        state.stop_event.set()

    finally:
        cleanup_resources(ff, picam, audio_thread, reader, state.stop_event)

    return restart_flag["do_restart"]


def main():
    global CHOSEN_FPS, GOP_SIZE
    global VIDEO_BITRATE, VIDEO_MAXRATE, VIDEO_BUFSIZE

    print(f"🌙 LOFI STREAMER {VERSION} — Woobot Pi4 Stable\n")

    state = StreamerState()

    def signal_handler(sig, frame):
        print("\n👋 Received shutdown signal")
        state.global_stop = True
        state.stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    wait_for_pi_ready()

    stream_url = load_stream_url()
    if not stream_url:
        return

    tracks = load_tracks()
    if not tracks:
        return

    CHOSEN_FPS, VIDEO_BITRATE, VIDEO_MAXRATE, VIDEO_BUFSIZE = choose_stream_params()
    GOP_SIZE = (CHOSEN_FPS or 20) * 4

    print(f"🎞 Final FPS: {CHOSEN_FPS}, GOP: {GOP_SIZE}")
    print(f"🔄 Auto-restart: {'Enabled' if AUTO_RESTART else 'Disabled'}")
    if SESSION_MAX_SECONDS > 0:
        print(f"🧼 Scheduled restart: every {SESSION_MAX_SECONDS}s")
    else:
        print("🧼 Scheduled restart: disabled")
    print()

    if not SKIP_NETWORK_CHECK and not check_network():
        print("⚠️ RTMP host unreachable right now (may still recover).")

    # Restart loop
    while not state.global_stop:
        print("🚀 Starting streaming session...")
        do_restart = run_streaming_session(state, stream_url)

        if state.global_stop:
            break

        if not AUTO_RESTART or not do_restart:
            print("🛑 Streaming stopped (restart not requested or auto-restart disabled).")
            break

        # Restart attempt throttling
        now = time.time()
        if now - state.last_restart_time < RESTART_COOLDOWN:
            state.restart_count += 1
        else:
            state.restart_count = 1
        state.last_restart_time = now

        if state.restart_count > MAX_RESTART_ATTEMPTS:
            print(f"❌ Max restart attempts ({MAX_RESTART_ATTEMPTS}) reached. Giving up.")
            break

        print(f"🔄 Restarting stream (attempt {state.restart_count}/{MAX_RESTART_ATTEMPTS})...")
        print(f"⏳ Waiting {RESTART_COOLDOWN}s before restart...")

        for _ in range(RESTART_COOLDOWN):
            if state.global_stop:
                break
            time.sleep(1)

        # Wait for network before restarting (prevents tight fail loops)
        if not check_network():
            print("⚠️ Waiting for network/RTMP connectivity...")
            while not check_network() and not state.global_stop:
                time.sleep(5)

    print("👋 Streamer shut down completely.")


if __name__ == "__main__":
    main()
