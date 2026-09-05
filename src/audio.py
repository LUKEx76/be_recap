import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np
import soundfile as sf

from src.config import TrackConfig
from src.parser import MemoryItem


@dataclass
class BeatEntry:
    """Represents a single memory mapped to an audio beat."""
    memory: MemoryItem
    track_index: int
    beat_index_in_track: int
    start_time: float
    duration: float
    frame_start: int
    frame_count: int


@dataclass
class AudioTimeline:
    """Complete audio timeline and memory mapping."""
    entries: List[BeatEntry]
    total_duration: float
    total_frames: int
    fps: int
    audio_file_path: Path


def build_timeline_and_audio(
    tracks: List[TrackConfig],
    memories: List[MemoryItem],
    fps: int,
    output_audio_path: Path,
) -> AudioTimeline:
    """
    Computes beat-accurate timings for each memory item and builds the synchronized audio file.
    
    Supports 1 or 2 tracks:
    - 1 track: plays 1 beat per memory at track[0].bpm.
    - 2 tracks: splits memories equally (chronological), playing the first half on track 1
      and the second half on track 2 with their respective BPMs.
      
    Fails fast if audio tracks are too short for the required beats.
    """
    total_memories = len(memories)
    if total_memories == 0:
        raise ValueError("Cannot build timeline with 0 memories.")
    if not (1 <= len(tracks) <= 2):
        raise ValueError(f"Expected 1 or 2 tracks, got {len(tracks)}")

    entries: List[BeatEntry] = []
    
    # 1. Determine memory partition per track
    if len(tracks) == 1:
        partitions = [(0, total_memories, tracks[0])]
    else:
        half = total_memories // 2
        partitions = [
            (0, half, tracks[0]),
            (half, total_memories, tracks[1]),
        ]

    audio_segments = []
    target_sr = 44100
    current_time = 0.0
    current_frame = 0

    for track_idx, (start_idx, end_idx, track_cfg) in enumerate(partitions):
        count = end_idx - start_idx
        if count == 0:
            continue
            
        beat_duration = 60.0 / track_cfg.bpm
        required_track_duration = count * beat_duration

        # Read audio file
        audio_data, sr = sf.read(str(track_cfg.path), always_2d=True)
        track_total_duration = len(audio_data) / sr

        # Validate sufficient audio length (fail-fast)
        start_sample_offset = int(track_cfg.start_offset_seconds * sr)
        needed_samples = int(required_track_duration * sr)
        
        if start_sample_offset + needed_samples > len(audio_data):
            available_after_offset = max(0.0, track_total_duration - track_cfg.start_offset_seconds)
            raise ValueError(
                f"Audio track {track_idx + 1} ('{track_cfg.path.name}') is too short! "
                f"Requires {required_track_duration:.2f}s ({count} beats at {track_cfg.bpm} BPM), "
                f"but only {available_after_offset:.2f}s is available after offset {track_cfg.start_offset_seconds:.2f}s."
            )

        # Slice audio samples
        sliced_audio = audio_data[start_sample_offset : start_sample_offset + needed_samples]

        # Resample if sample rate differs from 44.1kHz standard
        if sr != target_sr:
            # Linear interpolation resampling for clean audio without heavy deps
            num_target_samples = int(len(sliced_audio) * (target_sr / sr))
            indices = np.linspace(0, len(sliced_audio) - 1, num_target_samples)
            resampled = np.zeros((num_target_samples, sliced_audio.shape[1]), dtype=np.float32)
            for ch in range(sliced_audio.shape[1]):
                resampled[:, ch] = np.interp(indices, np.arange(len(sliced_audio)), sliced_audio[:, ch])
            sliced_audio = resampled

        audio_segments.append(sliced_audio)

        # Build beat entries for this partition
        for beat_i in range(count):
            mem_idx = start_idx + beat_i
            mem_item = memories[mem_idx]

            # Calculate frame boundaries to prevent rounding drift
            entry_start_time = current_time + (beat_i * beat_duration)
            entry_end_time = current_time + ((beat_i + 1) * beat_duration)

            f_start = round(entry_start_time * fps)
            f_end = round(entry_end_time * fps)
            f_count = max(1, f_end - f_start)

            entries.append(
                BeatEntry(
                    memory=mem_item,
                    track_index=track_idx,
                    beat_index_in_track=beat_i,
                    start_time=entry_start_time,
                    duration=beat_duration,
                    frame_start=f_start,
                    frame_count=f_count,
                )
            )

        current_time += required_track_duration
        current_frame = round(current_time * fps)

    # 2. Combine audio segments
    combined_audio = np.concatenate(audio_segments, axis=0) if len(audio_segments) > 1 else audio_segments[0]
    
    # 3. Write concatenated/trimmed audio to disk
    output_audio_path = Path(output_audio_path).resolve()
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_audio_path), combined_audio, target_sr, format="WAV")

    total_duration = len(combined_audio) / target_sr
    total_frames = entries[-1].frame_start + entries[-1].frame_count if entries else 0

    return AudioTimeline(
        entries=entries,
        total_duration=total_duration,
        total_frames=total_frames,
        fps=fps,
        audio_file_path=output_audio_path,
    )
