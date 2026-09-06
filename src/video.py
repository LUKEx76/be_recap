import subprocess
import sys
from pathlib import Path
from typing import Optional
import imageio_ffmpeg

from src.audio import AudioTimeline
from src.compositor import compose_frame, compose_year_card


def _get_year_end_timestamps(year: int):
    """
    Computes local and UTC datetime representations for Dec 31 23:59:59 of the given year
    based on the user's system timezone.
    
    This ensures that when gallery apps (Google Photos, Apple Photos) display the video
    in the user's local timezone, it appears exactly at Dec 31 23:59:59 rather than rolling
    over into Jan 1 of the following year.
    """
    import os
    import zoneinfo
    from datetime import datetime, timezone

    tz = None
    tz_env = os.environ.get("TZ")
    if tz_env:
        try:
            tz = zoneinfo.ZoneInfo(tz_env)
        except Exception:
            pass

    if tz is None:
        try:
            if os.path.exists("/etc/localtime") and os.path.islink("/etc/localtime"):
                parts = os.readlink("/etc/localtime").split("/")
                if "zoneinfo" in parts:
                    idx = parts.index("zoneinfo")
                    tz = zoneinfo.ZoneInfo("/".join(parts[idx + 1:]))
        except Exception:
            pass

    if tz is None:
        try:
            tz = datetime.now().astimezone().tzinfo
        except Exception:
            tz = timezone.utc

    local_dt = datetime(year, 12, 31, 23, 59, 59, tzinfo=tz)
    utc_dt = local_dt.astimezone(timezone.utc)
    return local_dt, utc_dt


def render_recap_video(
    timeline: AudioTimeline,
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
    year: Optional[int] = None,
    show_progress: bool = True,
) -> Path:
    """
    Renders the recap video by streaming raw RGB frames directly to an FFmpeg subprocess.
    
    Memory footprint: O(1) — exactly 1 uncompressed image in RAM at any given time.
    Performance: Each memory frame is composited once and duplicated across its beat frame count.
    Metadata: Sets internal creation_time and file modification time to Dec 31 23:59:59 of the target year.
    """
    import os

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    fps = timeline.fps
    total_entries = len(timeline.entries)
    
    if total_entries == 0:
        raise ValueError("Cannot render video with empty timeline entries.")
        
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",  # Video input (index 0)
        "-i", str(timeline.audio_file_path),  # Audio input (index 1)
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "25",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        "-shortest",
    ]

    # Add gallery date metadata (Dec 31 23:59:59 in local time)
    local_dt = None
    if year is not None:
        local_dt, utc_dt = _get_year_end_timestamps(year)
        utc_iso = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        local_iso = local_dt.isoformat()
        cmd.extend([
            "-metadata", f"creation_time={utc_iso}",
            "-metadata", f"date={local_iso}",
            "-metadata", f"com.apple.quicktime.creationdate={local_iso}",
            "-metadata:s:v:0", f"creation_time={utc_iso}",
            "-metadata:s:a:0", f"creation_time={utc_iso}",
        ])

    cmd.append(str(output_path))

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        total_rendered_frames = 0
        for i, entry in enumerate(timeline.entries):
            # Render frame in memory
            if entry.is_title_card:
                frame_img = compose_year_card(entry.card_text or (str(year) if year else ""), width=width, height=height)
            else:
                frame_img = compose_frame(entry.memory, width=width, height=height)

            raw_bytes = frame_img.tobytes("raw", "RGB")
            del frame_img  # Free memory immediately

            # Write raw frame for the exact duration of the beat
            for _ in range(entry.frame_count):
                process.stdin.write(raw_bytes)
                total_rendered_frames += 1

            if show_progress and ((i + 1) % 10 == 0 or (i + 1) == total_entries):
                percent = ((i + 1) / total_entries) * 100
                print(f"🎬 Progress: {i + 1}/{total_entries} memories rendered ({percent:.1f}%) [{total_rendered_frames}/{timeline.total_frames} frames]")
                sys.stdout.flush()

        process.stdin.close()
        stderr_output = process.stderr.read().decode("utf-8", errors="replace")
        ret_code = process.wait()

        if ret_code != 0:
            raise RuntimeError(f"FFmpeg failed with exit code {ret_code}:\n{stderr_output}")

        # Set filesystem modification & access time to Dec 31 23:59:59 in local time
        if year is not None and local_dt is not None:
            target_ts = local_dt.timestamp()
            os.utime(str(output_path), (target_ts, target_ts))

    except Exception as e:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.kill()
        raise e

    return output_path
