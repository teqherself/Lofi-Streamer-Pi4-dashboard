#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import shutil
import csv
import uuid

# -------------------------------------------------------
#  LOFI TRACK CLEANER — PRO EDITION (v3.2 BPM, 90s WAV)
#  GENDEMIK DIGITAL · Ms Stevie Woo
# -------------------------------------------------------

USER = os.environ.get("USER", "pi")
BASE_DIR = Path(f"/home/{USER}/LofiStream")
SOUNDS = BASE_DIR / "Sounds"
BACKUP = BASE_DIR / "Sounds_Originals"

PLAYLIST_OUT = BASE_DIR / "cleaned_playlist.txt"
ANALYSIS_CSV = BASE_DIR / "track_analysis.csv"

SUPPORTED = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
MAC_TRASH = {"._", ".DS_Store", "Thumbs.db"}

# Use RAM for temp WAVs if possible
TMP_DIR = Path("/dev/shm") if Path("/dev/shm").exists() else Path("/tmp")

# ----- AUBIO (BPM) -----
try:
    import aubio
    AUBIO_AVAILABLE = True
except ImportError:
    AUBIO_AVAILABLE = False


# -------------------------------------------------------
#  Helpers
# -------------------------------------------------------

def banner():
    print("\n🌙 LOFI TRACK CLEANER — PRO EDITION (v3.2 BPM)")
    print("---------------------------------------------------")
    print(f"🎵 Sounds folder: {SOUNDS}")
    print("🎧 Output: MP3 192k + EBU R128 + Trim + Fades")
    print("🧹 Features: junk deletion • corruption detection")
    print("             silence trim • fade in/out • playlist")
    if AUBIO_AVAILABLE:
        print("🪩 BPM detection: ENABLED (aubio, 90s WAV analysis)")
    else:
        print("🪩 BPM detection: DISABLED (install python3-aubio)")
    print("---------------------------------------------------\n")


def is_junk(name: str) -> bool:
    return name.startswith("._") or name in MAC_TRASH or name.startswith(".")


def ffprobe_duration(file: Path) -> float:
    """Return track duration in seconds (float) or -1 on error."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file),
            ],
            capture_output=True,
            text=True,
        )
        out = result.stdout.strip()
        if not out:
            return -1
        return float(out)
    except Exception:
        return -1


def is_corrupt(file: Path) -> bool:
    """Return True if ffprobe cannot read an audio stream."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-hide_banner", "-show_streams", str(file)],
            capture_output=True,
            text=True,
        )
        return "codec_type=audio" not in result.stdout
    except Exception:
        return True


def is_silent(file: Path) -> bool:
    """
    Check if track has near-zero amplitude.
    Uses ffmpeg volumedetect; flags if max_volume < -50 dB.
    """
    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-i", str(file),
            "-af", "volumedetect",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "max_volume" not in result.stderr:
            return False

        for line in result.stderr.splitlines():
            if "max_volume" in line:
                try:
                    vol = float(line.split(":")[1].replace(" dB", "").strip())
                    return vol < -50.0
                except Exception:
                    return False
        return False
    except Exception:
        return False


def build_audio_filter_chain(duration: float) -> str:
    """
    Build the ffmpeg -af filter chain:
      - Trim silence
      - Loudness normalisation
      - Fade in (1s)
      - Fade out (last 2s if duration known)
    """
    chain = (
        "silenceremove="
        "start_periods=1:start_threshold=-50dB:start_silence=0.2:"
        "stop_periods=1:stop_threshold=-50dB:stop_silence=0.5,"
        "loudnorm=I=-14:TP=-1.5:LRA=11,"
        "afade=t=in:st=0:d=1"
    )

    if duration > 4:
        fade_start = max(duration - 2.0, 0.5)
        chain += f",afade=t=out:st={fade_start:.3f}:d=2"

    return chain


def clean_one(src: Path, dst: Path, duration: float) -> bool:
    """Clean, trim, loudness-normalise and fade using ffmpeg."""
    try:
        afilter = build_audio_filter_chain(duration)

        cmd = [
            "ffmpeg",
            "-v", "error",
            "-i", str(src),
            "-vn",
            "-af", afilter,
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            "-map_metadata", "-1",
            "-y",
            str(dst),
        ]
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"⚠️ Failed to clean {src.name}: {e}")
        return False


def median(values):
    values = sorted(values)
    n = len(values)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return 0.5 * (values[mid - 1] + values[mid])


def estimate_bpm_wav(file: Path, max_analysis_time: float = 90.0) -> float:
    """
    Estimate BPM using aubio on a WAV file, analysing up to max_analysis_time seconds.
    Returns BPM as float, or -1.0 if unavailable.
    """
    if not AUBIO_AVAILABLE:
        return -1.0

    try:
        win_s = 1024
        hop_s = win_s // 2

        src = aubio.source(str(file), 0, hop_s)
        samplerate = src.samplerate

        tempo = aubio.tempo("default", win_s, hop_s, samplerate)

        beats = []
        total_time = 0.0

        while True:
            samples, read = src()
            is_beat = tempo(samples)

            if is_beat[0] == 1:
                this_beat = tempo.get_last_s()
                beats.append(this_beat)

            total_time += float(read) / float(samplerate)
            if read < hop_s or total_time >= max_analysis_time:
                break

        if len(beats) < 2:
            return -1.0

        intervals = [t1 - t0 for t0, t1 in zip(beats[:-1], beats[1:]) if t1 > t0]
        if not intervals:
            return -1.0

        avg_interval = median(intervals)
        if avg_interval <= 0:
            return -1.0

        bpm = 60.0 / avg_interval

        # Clamp to a sensible musical BPM range
        if bpm < 60:
            bpm *= 2
        if bpm > 200:
            bpm /= 2

        return round(bpm, 1)
    except Exception as e:
        print(f"   ⚠️ BPM estimation failed: {e}")
        return -1.0


def estimate_bpm_via_temp_wav(mp3_file: Path) -> float:
    """
    Decode first ~90s of the MP3 to a temporary mono WAV and run aubio on that.
    Cleans up the temp file afterwards.
    """
    if not AUBIO_AVAILABLE:
        return -1.0

    tmp_name = f"bpm_{uuid.uuid4().hex}.wav"
    tmp_wav = TMP_DIR / tmp_name

    try:
        # Decode first 90 seconds to mono 44.1k WAV
        cmd = [
            "ffmpeg",
            "-v", "error",
            "-t", "90",
            "-i", str(mp3_file),
            "-ac", "1",
            "-ar", "44100",
            "-y",
            str(tmp_wav),
        ]
        subprocess.run(cmd, check=True)

        bpm = estimate_bpm_wav(tmp_wav, max_analysis_time=90.0)
        return bpm
    except Exception as e:
        print(f"   ⚠️ Failed to create temp WAV for BPM: {e}")
        return -1.0
    finally:
        try:
            if tmp_wav.exists():
                tmp_wav.unlink()
        except Exception:
            pass


# -------------------------------------------------------
#  Main
# -------------------------------------------------------

def main():
    banner()

    if not SOUNDS.exists():
        print("❌ Sounds folder missing!")
        return

    BACKUP.mkdir(exist_ok=True)

    # Remove junk files (Mac metadata etc.)
    removed_junk = 0
    for f in list(SOUNDS.iterdir()):
        if is_junk(f.name):
            print(f"🗑 Removing junk file: {f.name}")
            try:
                f.unlink()
                removed_junk += 1
            except Exception as e:
                print(f"   ⚠️ Could not remove: {e}")

    print(f"\n🧹 Junk files removed: {removed_junk}")

    # Collect audio files
    files = [
        f for f in SOUNDS.iterdir()
        if f.suffix.lower() in SUPPORTED and not is_junk(f.name)
    ]

    if not files:
        print("❌ No valid audio files found.")
        return

    print(f"🔍 Found {len(files)} audio files to inspect.\n")

    cleaned = 0
    skipped = 0
    silent_count = 0
    corrupt_count = 0

    playlist_entries = []
    analysis_rows = []

    for f in files:
        print(f"→ Processing: {f.name}")

        # Corruption check
        if is_corrupt(f):
            print("   ⚠️ Corrupt file removed.")
            try:
                f.unlink()
            except Exception as e:
                print(f"   ⚠️ Could not delete corrupt file: {e}")
            corrupt_count += 1
            continue

        # Duration
        dur = ffprobe_duration(f)
        if dur <= 0:
            print("   ⚠️ Could not determine duration, cleaning without precise fade-out.")
            dur = -1

        # Silence check
        silent_flag = is_silent(f)
        if silent_flag:
            print("   🤫 File appears very quiet / mostly silence.")
            silent_count += 1

        # Clean and convert
        dst = SOUNDS / (f.stem + "_clean.mp3")

        if clean_one(f, dst, dur):
            # Backup original
            try:
                shutil.move(str(f), BACKUP / f.name)
            except Exception as e:
                print(f"   ⚠️ Could not move original to backup: {e}")

            final = SOUNDS / (f.stem + ".mp3")
            try:
                dst.rename(final)
            except Exception as e:
                print(f"   ⚠️ Could not rename cleaned file: {e}")
                skipped += 1
                continue

            playlist_entries.append(final.name)
            cleaned += 1
            print(f"   ✔ Cleaned → {final.name}")

            # BPM using temp WAV
            bpm = estimate_bpm_via_temp_wav(final)
            if bpm > 0:
                print(f"   🪩 Estimated BPM: {bpm}")
            else:
                if AUBIO_AVAILABLE:
                    print("   🪩 BPM: could not determine")
                else:
                    print("   🪩 BPM: aubio not installed")

            print()

            analysis_rows.append({
                "filename": final.name,
                "duration_sec": f"{dur:.2f}" if dur > 0 else "",
                "silent_warning": "yes" if silent_flag else "no",
                "bpm_estimate": f"{bpm:.1f}" if bpm > 0 else "",
            })
        else:
            skipped += 1
            print("   ✖ Cleaning failed.\n")

    # Write cleaned playlist
    if playlist_entries:
        try:
            with PLAYLIST_OUT.open("w") as pl:
                for track in playlist_entries:
                    pl.write(track + "\n")
        except Exception as e:
            print(f"⚠️ Could not write playlist file: {e}")

    # Write analysis CSV
    if analysis_rows:
        try:
            with ANALYSIS_CSV.open("w", newline="") as csvfile:
                fieldnames = ["filename", "duration_sec", "silent_warning", "bpm_estimate"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in analysis_rows:
                    writer.writerow(row)
        except Exception as e:
            print(f"⚠️ Could not write analysis CSV: {e}")

    # Summary
    print("\n---------------------------------------------------")
    print("✨ CLEANING SUMMARY (v3.2 BPM)")
    print(f"🎧 Cleaned tracks: {cleaned}")
    print(f"🚫 Skipped errors: {skipped}")
    print(f"❌ Corrupt removed: {corrupt_count}")
    print(f"🤫 Silent warnings: {silent_count}")
    print(f"📦 Original backups: {BACKUP}")
    print(f"📝 Playlist file: {PLAYLIST_OUT}")
    print(f"📊 Analysis CSV:   {ANALYSIS_CSV}")
    print("---------------------------------------------------\n")


if __name__ == "__main__":
    main()
