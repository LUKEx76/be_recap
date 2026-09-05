import subprocess
import sys
from pathlib import Path
from typing import Optional
import imageio_ffmpeg

from src.audio import AudioTimeline
from src.compositor import compose_frame


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
    from datetime import datetime, timezone

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
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        "-shortest",
    ]

    # Add gallery date metadata (Dec 31 23:59:59 of given year)
    if year is not None:
        creation_ts = f"{year}-12-31T23:59:59Z"
        cmd.extend([
            "-metadata", f"creation_time={creation_ts}",
            "-metadata", f"date={year}-12-31",
            "-metadata:s:v:0", f"creation_time={creation_ts}",
            "-metadata:s:a:0", f"creation_time={creation_ts}",
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

        # Set filesystem modification & access time to Dec 31 23:59:59 of target year
        if year is not None:
            target_dt = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            target_ts = target_dt.timestamp()
            os.utime(str(output_path), (target_ts, target_ts))

    except Exception as e:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.kill()
        raise e

    return output_path
