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
    
    # 1. Sequentially assign memories to tracks until all memories are covered
    audio_segments = []
    target_sr = 44100
    current_time = 0.0
    current_frame = 0
    remaining_memories = total_memories
    mem_cursor = 0

    for track_idx, track_cfg in enumerate(tracks):
        if remaining_memories <= 0:
            break

        beat_duration = 60.0 / track_cfg.bpm

        # Read audio file
        audio_data, sr = sf.read(str(track_cfg.path), always_2d=True)
        track_total_duration = len(audio_data) / sr
        available_seconds = track_total_duration - track_cfg.start_offset_seconds

        if available_seconds <= 0:
            raise ValueError(
                f"Audio track {track_idx + 1} ('{track_cfg.path.name}') has offset {track_cfg.start_offset_seconds:.2f}s "
                f"which exceeds total track duration of {track_total_duration:.2f}s."
            )

        # Max beats this track can provide after offset
        max_beats_in_track = int(available_seconds / beat_duration)
        if max_beats_in_track == 0:
            continue

        # Assign as many memories as this track can cover
        beats_to_take = min(remaining_memories, max_beats_in_track)
        required_track_duration = beats_to_take * beat_duration

        start_sample_offset = int(track_cfg.start_offset_seconds * sr)
        needed_samples = int(required_track_duration * sr)

        # Slice audio samples
        sliced_audio = audio_data[start_sample_offset : start_sample_offset + needed_samples]

        # Resample if sample rate differs from 44.1kHz standard
        if sr != target_sr:
            num_target_samples = int(len(sliced_audio) * (target_sr / sr))
            indices = np.linspace(0, len(sliced_audio) - 1, num_target_samples)
            resampled = np.zeros((num_target_samples, sliced_audio.shape[1]), dtype=np.float32)
            for ch in range(sliced_audio.shape[1]):
                resampled[:, ch] = np.interp(indices, np.arange(len(sliced_audio)), sliced_audio[:, ch])
            sliced_audio = resampled

        # Ensure 2 channels (stereo)
        if sliced_audio.shape[1] == 1:
            sliced_audio = np.repeat(sliced_audio, 2, axis=1)

        audio_segments.append(sliced_audio)

        # Build beat entries for this track's slice
        for beat_i in range(beats_to_take):
            mem_item = memories[mem_cursor]
            mem_cursor += 1

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
        remaining_memories -= beats_to_take

    # If all tracks were exhausted and memories still remain, fail fast
    if remaining_memories > 0:
        covered = total_memories - remaining_memories
        raise ValueError(
            f"Provided audio tracks are too short for all {total_memories} memories! "
            f"The tracks covered {covered} memories ({current_time:.2f}s), but {remaining_memories} memories still remain."
        )

    # 2. Combine audio segments
    combined_audio = np.concatenate(audio_segments, axis=0) if len(audio_segments) > 1 else audio_segments[0]
    
    # Normalize peak volume to -0.5 dB (0.95 amplitude) for crisp, audible sound
    peak = np.max(np.abs(combined_audio))
    if peak > 0:
        combined_audio = (combined_audio / peak) * 0.95

    # 3. Write concatenated/trimmed audio to disk
    output_audio_path = Path(output_audio_path).resolve()
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_audio_path), combined_audio, target_sr, format="WAV", subtype="PCM_16")

    total_duration = len(combined_audio) / target_sr
    total_frames = entries[-1].frame_start + entries[-1].frame_count if entries else 0

    return AudioTimeline(
        entries=entries,
        total_duration=total_duration,
        total_frames=total_frames,
        fps=fps,
        audio_file_path=output_audio_path,
    )
