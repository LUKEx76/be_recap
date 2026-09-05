import argparse
import sys
import time
from pathlib import Path

from src.config import AppConfig
from src.parser import parse_memories
from src.audio import build_timeline_and_audio
from src.video import render_recap_video


def run(config_path: str | Path) -> None:
    """Execute the BeReal recap generation pipeline."""
    start_time = time.time()
    print("=" * 60)
    print("📸 BeReal Recap Video Generator")
    print("=" * 60)

    # 1. Load and validate configuration
    print(f"⚙️  Loading configuration from: {config_path}")
    config = AppConfig.load_from_file(config_path)
    print(f"🎯 Target Year: {config.year}")
    print(f"📁 BeReal Export: {config.export_dir}")
    print(f"🎵 Tracks ({len(config.tracks)}):")
    for idx, t in enumerate(config.tracks, 1):
        print(f"   [{idx}] {t.path.name} @ {t.bpm} BPM (offset: {t.start_offset_seconds}s)")
    print(f"📐 Resolution: {config.width}x{config.height} @ {config.fps} fps")

    # 2. Parse & validate memories
    print("\n🔍 Parsing and filtering memories...")
    memories = parse_memories(
        export_dir=config.export_dir,
        target_year=config.year,
        date_format=config.date_format,
    )
    print(f"✅ Found {len(memories)} memories for year {config.year}")
    print(f"   Earliest: {memories[0].formatted_date} ({memories[0].location_name or 'No location'})")
    print(f"   Latest:   {memories[-1].formatted_date} ({memories[-1].location_name or 'No location'})")

    # 3. Compute beat timeline & assemble audio
    print("\n🎵 Calculating beat synchronization and assembling audio...")
    temp_audio_path = config.output_path.parent / f".tmp_audio_{config.year}.wav"
    timeline = build_timeline_and_audio(
        tracks=config.tracks,
        memories=memories,
        fps=config.fps,
        output_audio_path=temp_audio_path,
    )
    print(f"✅ Audio timeline generated: {timeline.total_duration:.2f}s total ({timeline.total_frames} frames)")

    # 4. Render video frames with zero-memory streaming
    print(f"\n🎥 Rendering video to {config.output_path}...")
    render_recap_video(
        timeline=timeline,
        output_path=config.output_path,
        width=config.width,
        height=config.height,
        year=config.year,
        show_progress=True,
    )

    # Clean up temporary audio file
    if temp_audio_path.exists():
        try:
            temp_audio_path.unlink()
        except Exception:
            pass

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎉 Recap generation complete in {elapsed:.1f}s!")
    print(f"💾 Output saved to: {config.output_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate beat-synced BeReal year recap videos."
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config.json",
        help="Path to the JSON configuration file (default: config.json)",
    )
    args = parser.parse_args()

    try:
        run(args.config)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
