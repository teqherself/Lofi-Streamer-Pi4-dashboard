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
#  LOFI STREAMER v8.7.10 — STABILITY IMPROVEMENTS
# ======================================================================
#  ✔ Auto-reconnect on stream failure
#  ✔ Circular buffer for camera FIFO to prevent overflow
#  ✔ Watchdog monitoring for FFmpeg health
#  ✔ Graceful error recovery
#  ✔ Process cleanup improvements
# ======================================================================

VERSION = "8.7.10-woobot-stable"

OUTPUT_W = 1280
OUTPUT_H = 720

LOGO_PADDING = 40
TEXT_PADDING = 40

CAM_FIFO = Path("/tmp/camfifo.ts")
AUDIO_FIFO = Path("/tmp/lofi_audio.pcm")

NOWPLAYING_FILE = Path("/tmp/nowplaying.txt")
CURRENT_TRACK_FILE = Path("/tmp/current_track.txt")

# Watchdog settings
WATCHDOG_INTERVAL = 30  # Check every 30 seconds
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 60  # Wait 60s between restart attempts

CHOSEN_FPS: Optional[int] = None
GOP_SIZE: Optional[int] = None

VIDEO_BITRATE = "1800k"
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
# DIRS
# -------------------------------------------------------
PLAYLIST_DIR = _env_path("LOFI_PLAYLIST_DIR", BASE_DIR / "Sounds")
LOGO_DIR = _env_path("LOFI_BRAND_DIR", BASE_DIR / "Logo")

STREAM_URL_FILE = _env_path("LOFI_STREAM_URL_FILE", BASE_DIR / "stream_url.txt")
STREAM_URL_ENV = os.environ.get("LOFI_YOUTUBE_URL", "")

FFMPEG_LOGO = _env_path("LOFI_BRAND_IMAGE", LOGO_DIR / "picam.png")

FALLBACK_FPS = _env_int("LOFI_FALLBACK_FPS", 25)

CHECK_HOST = os.environ.get("LOFI_CHECK_HOST", "a.rtmp.youtube.com")
CHECK_PORT = _env_int("LOFI_CHECK_PORT", 1935)

SKIP_NETWORK_CHECK = _env_bool("LOFI_SKIP_NETWORK_CHECK")

# Auto-restart configuration
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
    bitrate = "1800k"
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


def _playlist_iterator():
    while True:
        tracks = load_tracks()
        if not tracks:
            print("⚠️ No tracks found. Waiting 10 seconds before retry...")
            time.sleep(10)
            continue

        lst = list(tracks)
        random.shuffle(lst)
        for t in lst:
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
# CIRCULAR FIFO OUTPUT (prevents camera overflow)
# -------------------------------------------------------
class CircularFifoOutput(FileOutput):
    """
    Wraps FileOutput to handle FIFO blocking gracefully.
    If writes would block, drop frames instead of stalling the camera.
    """
    def __init__(self, file, buffer_size=1024*1024):
        super().__init__(file)
        self.buffer_size = buffer_size
        self.dropped_frames = 0
        self.non_blocking_set = False
    
    def outputframe(self, frame, keyframe=True, timestamp=None, packet=None, audio=None):
        try:
            # Set non-blocking on the FIFO (only once)
            if not self.non_blocking_set and hasattr(self, 'file') and hasattr(self.file, 'fileno'):
                try:
                    fd = self.file.fileno()
                    import fcntl
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                    self.non_blocking_set = True
                except Exception:
                    pass
            
            # Call parent with all arguments
            super().outputframe(frame, keyframe, timestamp, packet, audio)
        except BlockingIOError:
            # FFmpeg not reading fast enough - drop this frame
            self.dropped_frames += 1
            if self.dropped_frames % 100 == 0:
                print(f"⚠️ Dropped {self.dropped_frames} camera frames (FIFO full)")
        except Exception as e:
            print(f"❌ Camera output error: {e}")


# -------------------------------------------------------
# CAMERA
# -------------------------------------------------------
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

    def _br_to_int(br: str) -> int:
        if br.endswith("k"):
            return int(br[:-1]) * 1000
        return int(br)

    encoder = H264Encoder(bitrate=_br_to_int(VIDEO_BITRATE))
    
    # Use circular buffer output to prevent overflow
    out = CircularFifoOutput(str(CAM_FIFO))

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
# AUDIO FEEDER (with better error handling)
# -------------------------------------------------------
def audio_feeder(_tracks_unused, stop_event):
    print("🎚 Audio feeder started.")

    try:
        with open(AUDIO_FIFO, "wb", buffering=0) as fd:
            for t in _playlist_iterator():

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
                
                try:
                    p = subprocess.Popen(cmd, stdout=fd, stderr=subprocess.PIPE)

                    while p.poll() is None and not stop_event.is_set():
                        time.sleep(0.5)

                    if stop_event.is_set():
                        try:
                            p.terminate()
                            p.wait(timeout=2)
                        except Exception:
                            p.kill()
                        break
                    
                    # Check if ffmpeg failed
                    if p.returncode != 0:
                        stderr = p.stderr.read().decode() if p.stderr else ""
                        print(f"⚠️ FFmpeg audio decode error for {t.name}: {stderr}")
                        continue
                        
                except BrokenPipeError:
                    print("⚠️ Audio FIFO broken pipe - FFmpeg may have stopped")
                    break
                except Exception as e:
                    print(f"❌ Audio feeder error: {e}")
                    if stop_event.is_set():
                        break
                    time.sleep(1)
                    
    except Exception as e:
        print(f"❌ Audio feeder fatal error: {e}")

    print("🎚 Audio feeder stopped.")


# -------------------------------------------------------
# FFMPEG PIPELINE (with stderr logging)
# -------------------------------------------------------
def start_pipeline(stream_url: str):
    print("🎥 Starting ffmpeg pipeline…")

    g = GOP_SIZE

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",  # Changed to warning for better debugging
        "-fflags", "+genpts+discardcorrupt",
        "-flags", "low_delay",
        "-thread_queue_size", "4096",
        "-probesize", "64k",
        "-analyzeduration", "0",
        "-vsync", "1",
        "-use_wallclock_as_timestamps", "1",
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
        "-f", "flv", stream_url
    ]

    return subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)


# -------------------------------------------------------
# WATCHDOG (monitors FFmpeg health)
# -------------------------------------------------------
def watchdog_monitor(ff_process, stop_event, restart_callback):
    """
    Monitor FFmpeg process and trigger restart if it becomes unhealthy.
    """
    print("🐕 Watchdog started")
    
    last_check_time = time.time()
    
    while not stop_event.is_set():
        time.sleep(WATCHDOG_INTERVAL)
        
        if stop_event.is_set():
            break
            
        # Check if FFmpeg is still running
        if ff_process.poll() is not None:
            print("❌ Watchdog: FFmpeg process died")
            
            # Read any error output
            try:
                stderr = ff_process.stderr.read().decode() if ff_process.stderr else ""
                if stderr:
                    print(f"FFmpeg stderr: {stderr[-500:]}")  # Last 500 chars
            except Exception:
                pass
            
            restart_callback()
            break
        
        # Check CPU usage if psutil available
        if PSUTIL_AVAILABLE:
            try:
                cpu = psutil.cpu_percent(interval=1)
                if cpu > 95:
                    print(f"⚠️ Watchdog: High CPU usage ({cpu:.1f}%)")
            except Exception:
                pass
        
        # Verify network connectivity periodically (every 5 minutes)
        if time.time() - last_check_time > 300:
            if not check_network():
                print("⚠️ Watchdog: Network connectivity lost")
            last_check_time = time.time()
    
    print("🐕 Watchdog stopped")


# -------------------------------------------------------
# MAIN LOOP with AUTO-RESTART
# -------------------------------------------------------
class StreamerState:
    def __init__(self):
        self.should_restart = False
        self.restart_count = 0
        self.last_restart_time = 0
        self.stop_event = threading.Event()
        self.global_stop = False


def cleanup_resources(ff, picam, audio_thread, stop_event):
    """Clean up all streaming resources"""
    print("🧹 Cleaning up resources...")
    
    stop_event.set()
    
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
    
    # Stop camera
    stop_camera(picam)
    
    # Wait for audio thread
    if audio_thread and audio_thread.is_alive():
        try:
            audio_thread.join(timeout=3)
        except Exception:
            pass


def run_streaming_session(state: StreamerState, stream_url: str):
    """Run one streaming session"""
    
    # Reset stop event for this session
    state.stop_event.clear()
    
    # Create FIFOs
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

    # Start pipeline
    ff = start_pipeline(stream_url)
    if not ff:
        print("❌ Failed to start FFmpeg")
        return False
    
    # Start camera
    picam = start_camera()
    if not picam:
        print("❌ Failed to start camera")
        try:
            ff.terminate()
        except Exception:
            pass
        return False

    # Start audio
    tracks = load_tracks()
    audio_thread = threading.Thread(
        target=audio_feeder, args=(tracks, state.stop_event), daemon=True
    )
    audio_thread.start()

    # Start watchdog
    def restart_trigger():
        state.should_restart = True
        state.stop_event.set()
    
    watchdog_thread = threading.Thread(
        target=watchdog_monitor, 
        args=(ff, state.stop_event, restart_trigger),
        daemon=True
    )
    watchdog_thread.start()

    # Main monitoring loop
    try:
        while not state.stop_event.is_set() and not state.global_stop:
            if ff.poll() is not None:
                print("❌ FFmpeg exited")
                state.should_restart = True
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print("👋 Stopping streamer...")
        state.global_stop = True

    finally:
        cleanup_resources(ff, picam, audio_thread, state.stop_event)

    return True


def main():
    global CHOSEN_FPS, GOP_SIZE
    global VIDEO_BITRATE, VIDEO_MAXRATE, VIDEO_BUFSIZE

    print(f"🌙 LOFI STREAMER v{VERSION} — Woobot Stable\n")

    # Handle Ctrl+C gracefully
    state = StreamerState()
    
    def signal_handler(sig, frame):
        print("\n👋 Received shutdown signal")
        state.global_stop = True
        state.stop_event.set()
        sys.exit(0)
    
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
    GOP_SIZE = CHOSEN_FPS * 4

    print(f"🎞 Final FPS: {CHOSEN_FPS}, GOP: {GOP_SIZE}")
    print(f"🔄 Auto-restart: {'Enabled' if AUTO_RESTART else 'Disabled'}\n")

    if not SKIP_NETWORK_CHECK and not check_network():
        print("⚠️ RTMP host unreachable.")

    # Main restart loop
    while not state.global_stop:
        print("🚀 Starting streaming session...")
        
        success = run_streaming_session(state, stream_url)
        
        if state.global_stop:
            break
        
        if not AUTO_RESTART or not state.should_restart:
            print("❌ Streaming stopped and auto-restart disabled")
            break
        
        # Check restart limits
        current_time = time.time()
        if current_time - state.last_restart_time < RESTART_COOLDOWN:
            state.restart_count += 1
        else:
            state.restart_count = 1
        
        state.last_restart_time = current_time
        
        if state.restart_count > MAX_RESTART_ATTEMPTS:
            print(f"❌ Max restart attempts ({MAX_RESTART_ATTEMPTS}) reached. Giving up.")
            break
        
        print(f"🔄 Restarting stream (attempt {state.restart_count}/{MAX_RESTART_ATTEMPTS})...")
        print(f"⏳ Waiting {RESTART_COOLDOWN}s before restart...")
        
        # Wait for cooldown period (can be interrupted)
        for _ in range(RESTART_COOLDOWN):
            if state.global_stop:
                break
            time.sleep(1)
        
        if state.global_stop:
            break
        
        # Reset restart flag
        state.should_restart = False
        
        # Check network before restart
        if not check_network():
            print("⚠️ Waiting for network connectivity...")
            while not check_network() and not state.global_stop:
                time.sleep(5)

    print("👋 Streamer shut down completely.")


if __name__ == "__main__":
    main()
