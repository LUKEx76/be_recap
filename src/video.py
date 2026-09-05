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
    show_progress: bool = True,
) -> Path:
    """
    Renders the recap video by streaming raw RGB frames directly to an FFmpeg subprocess.
    
    Memory footprint: O(1) — exactly 1 uncompressed image in RAM at any given time.
    Performance: Each memory frame is composited once and duplicated across its beat frame count.
    """
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
        "-i", "-",  # Video input from stdin
        "-i", str(timeline.audio_file_path),  # Audio input from file
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

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

    except Exception as e:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.kill()
        raise e

    return output_path
