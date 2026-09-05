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
    """Represents a single memory or title card mapped to an audio beat."""
    memory: Optional[MemoryItem]
    track_index: int
    beat_index_in_track: int
    start_time: float
    duration: float
    frame_start: int
    frame_count: int
    is_title_card: bool = False
    card_text: Optional[str] = None


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
    year: Optional[int] = None,
) -> AudioTimeline:
    """
    Computes beat-accurate timings for intro card, memories, and outro card,
    and builds the synchronized audio file with outro fade-out.
    
    - Prepends a black intro card showing the year for 2x memory duration.
    - Appends a black outro card showing the year for 2x memory duration.
    - Fades out audio smoothly over the outro card duration.
    """
    total_memories = len(memories)
    if total_memories == 0:
        raise ValueError("Cannot build timeline with 0 memories.")
    if len(tracks) == 0:
        raise ValueError("Must provide at least 1 audio track.")

    if year is None:
        year = memories[0].date.year

    entries: List[BeatEntry] = []
    audio_segments = []
    target_sr = 44100
    current_time = 0.0

    # Intro duration: 2x memory duration of track 0
    track0_mem_dur = (60.0 / tracks[0].bpm) * tracks[0].beats_per_memory
    intro_duration = 2.0 * track0_mem_dur

    # 1. Add Intro Title Card Entry
    intro_f_start = 0
    intro_f_end = round(intro_duration * fps)
    intro_f_count = max(1, intro_f_end - intro_f_start)
    entries.append(
        BeatEntry(
            memory=None,
            track_index=0,
            beat_index_in_track=0,
            start_time=0.0,
            duration=intro_duration,
            frame_start=intro_f_start,
            frame_count=intro_f_count,
            is_title_card=True,
            card_text=str(year),
        )
    )
    current_time += intro_duration

    remaining_memories = total_memories
    mem_cursor = 0
    last_used_track_cfg = tracks[0]
    last_used_track_idx = 0

    # 2. Allocate memories (and intro/outro durations) across tracks
    for track_idx, track_cfg in enumerate(tracks):
        if remaining_memories <= 0:
            break

        last_used_track_cfg = track_cfg
        last_used_track_idx = track_idx

        single_beat_duration = 60.0 / track_cfg.bpm
        memory_duration = single_beat_duration * track_cfg.beats_per_memory

        # Read audio file
        audio_data, sr = sf.read(str(track_cfg.path), always_2d=True)
        track_raw_duration = len(audio_data) / sr

        if track_cfg.start_offset_seconds < 0:
            # Negative offset: prepend silence to delay audio playback
            silence_samples = int(abs(track_cfg.start_offset_seconds) * sr)
            silence = np.zeros((silence_samples, audio_data.shape[1]), dtype=audio_data.dtype)
            audio_data = np.concatenate([silence, audio_data], axis=0)
            available_seconds = len(audio_data) / sr
            start_sample_offset = 0
        else:
            # Positive offset: trim beginning of song
            available_seconds = track_raw_duration - track_cfg.start_offset_seconds
            if available_seconds <= 0:
                raise ValueError(
                    f"Audio track {track_idx + 1} ('{track_cfg.path.name}') has offset {track_cfg.start_offset_seconds:.2f}s "
                    f"which exceeds total track duration of {track_raw_duration:.2f}s."
                )
            start_sample_offset = int(track_cfg.start_offset_seconds * sr)

        # Extra duration for intro if on track 0
        extra_lead_dur = intro_duration if track_idx == 0 else 0.0
        remaining_sec_for_memories = available_seconds - extra_lead_dur

        if remaining_sec_for_memories <= 0:
            continue

        # Max memories this track can cover
        max_memories_in_track = int(remaining_sec_for_memories / memory_duration)
        if max_memories_in_track == 0:
            continue

        memories_to_take = min(remaining_memories, max_memories_in_track)
        required_track_duration = extra_lead_dur + (memories_to_take * memory_duration)

        needed_samples = int(required_track_duration * sr)
        sliced_audio = audio_data[start_sample_offset : start_sample_offset + needed_samples]

        # Resample if needed
        if sr != target_sr:
            num_target_samples = int(len(sliced_audio) * (target_sr / sr))
            indices = np.linspace(0, len(sliced_audio) - 1, num_target_samples)
            resampled = np.zeros((num_target_samples, sliced_audio.shape[1]), dtype=np.float32)
            for ch in range(sliced_audio.shape[1]):
                resampled[:, ch] = np.interp(indices, np.arange(len(sliced_audio)), sliced_audio[:, ch])
            sliced_audio = resampled

        if sliced_audio.shape[1] == 1:
            sliced_audio = np.repeat(sliced_audio, 2, axis=1)

        audio_segments.append(sliced_audio)

        # Build beat entries for memories
        for mem_i in range(memories_to_take):
            mem_item = memories[mem_cursor]
            mem_cursor += 1

            entry_start_time = current_time + (mem_i * memory_duration)
            entry_end_time = current_time + ((mem_i + 1) * memory_duration)

            f_start = round(entry_start_time * fps)
            f_end = round(entry_end_time * fps)
            f_count = max(1, f_end - f_start)

            entries.append(
                BeatEntry(
                    memory=mem_item,
                    track_index=track_idx,
                    beat_index_in_track=mem_i,
                    start_time=entry_start_time,
                    duration=memory_duration,
                    frame_start=f_start,
                    frame_count=f_count,
                    is_title_card=False,
                )
            )

        current_time += (memories_to_take * memory_duration)
        remaining_memories -= memories_to_take

    if remaining_memories > 0:
        covered = total_memories - remaining_memories
        raise ValueError(
            f"Provided audio tracks are too short for all {total_memories} memories (+ intro/outro)! "
            f"The tracks covered {covered} memories ({current_time:.2f}s), but {remaining_memories} memories still remain."
        )

    # 3. Add Outro Title Card Entry & Outro Audio
    outro_mem_dur = (60.0 / last_used_track_cfg.bpm) * last_used_track_cfg.beats_per_memory
    outro_duration = 2.0 * outro_mem_dur

    outro_f_start = round(current_time * fps)
    outro_f_end = round((current_time + outro_duration) * fps)
    outro_f_count = max(1, outro_f_end - outro_f_start)

    entries.append(
        BeatEntry(
            memory=None,
            track_index=last_used_track_idx,
            beat_index_in_track=len(entries),
            start_time=current_time,
            duration=outro_duration,
            frame_start=outro_f_start,
            frame_count=outro_f_count,
            is_title_card=True,
            card_text=str(year),
        )
    )

    # Append outro audio samples from last track if available, or generate extra samples
    audio_data_last, sr_last = sf.read(str(last_used_track_cfg.path), always_2d=True)
    # Get extra outro samples
    needed_outro_samples = int(outro_duration * target_sr)
    # Extract extra samples from track or pad
    if last_used_track_cfg.start_offset_seconds < 0:
        silence_samples = int(abs(last_used_track_cfg.start_offset_seconds) * sr_last)
        silence = np.zeros((silence_samples, audio_data_last.shape[1]), dtype=audio_data_last.dtype)
        audio_data_last = np.concatenate([silence, audio_data_last], axis=0)
        start_sample_offset = 0
    else:
        start_sample_offset = int(last_used_track_cfg.start_offset_seconds * sr_last)

    # Total samples used so far from last track
    last_segment_len = len(audio_segments[-1])
    extra_start = start_sample_offset + last_segment_len
    extra_end = extra_start + needed_outro_samples
    if extra_end <= len(audio_data_last):
        extra_slice = audio_data_last[extra_start:extra_end]
        if sr_last != target_sr:
            num_target = int(len(extra_slice) * (target_sr / sr_last))
            indices = np.linspace(0, len(extra_slice) - 1, num_target)
            resampled = np.zeros((num_target, extra_slice.shape[1]), dtype=np.float32)
            for ch in range(extra_slice.shape[1]):
                resampled[:, ch] = np.interp(indices, np.arange(len(extra_slice)), extra_slice[:, ch])
            extra_slice = resampled
        if extra_slice.shape[1] == 1:
            extra_slice = np.repeat(extra_slice, 2, axis=1)
        audio_segments.append(extra_slice)
    else:
        # Pad silence if track ran out
        pad = np.zeros((needed_outro_samples, 2), dtype=np.float32)
        audio_segments.append(pad)

    current_time += outro_duration

    # 4. Combine audio segments
    combined_audio = np.concatenate(audio_segments, axis=0)
    
    # Peak volume normalization
    peak = np.max(np.abs(combined_audio))
    if peak > 0:
        combined_audio = (combined_audio / peak) * 0.95

    # 5. Apply smooth fade-out over outro duration
    outro_sample_count = int(outro_duration * target_sr)
    if outro_sample_count > 0 and len(combined_audio) >= outro_sample_count:
        fade_curve = np.linspace(1.0, 0.0, outro_sample_count, dtype=np.float32)[:, np.newaxis]
        combined_audio[-outro_sample_count:] *= fade_curve

    # 6. Write to disk
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
