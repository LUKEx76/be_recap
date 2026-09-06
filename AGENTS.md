# AGENTS.md — AI Agent Guide for `be_recap`

Welcome to **be_recap**, a Python-based multimedia processing pipeline designed to generate vertical BeReal year-in-review recap videos synced to audio BPM.

---

## 🎯 Project Objective

Generate high-quality 9:16 vertical recap videos from an exported BeReal archive for any selected year:
1. **Beat Syncing**: Display exactly 1 (or $N$) BeReal memory per beat based on user-provided music tracks (1–2 songs), BPMs, and offsets.
2. **Authentic BeReal Layout**:
   - **Background**: Large full-frame primary/back camera photo (scaled and center-cropped to 1080x1920).
   - **Top-Left PIP**: Front-facing selfie camera photo with rounded corners and a subtle white border.
   - **Top-Right Overlay**: Date (`DD.MM.YYYY`) and Location (`City, Country` via reverse geocoding).
   - **Bottom Overlay**: Caption with adaptive font sizing and emoji rendering (`pilmoji`) to prevent overflow and ensure legibility.
3. **Sequential Audio Chaining**: Support 1 or 2 sequential audio tracks, smoothly transitioning audio, per-track BPMs, and frame timing.
4. **Timezone-Aware Gallery Metadata**: Set video container `creation_time` and filesystem modification timestamps to Dec 31 23:59:59 in the user's local timezone so that gallery apps (Google Photos, Apple Photos) display the video at the end of the year.

---

## 🏗️ Architecture & Modules

The project follows a clean, modular structure:

```
be_recap/
├── configs/               # User and example JSON configurations
│   └── config.example.json
├── data/                  # Git-ignored local BeReal export folders
├── songs/                 # Git-ignored local audio files
├── src/
│   ├── __init__.py
│   ├── config.py          # Pydantic configuration schema (AppConfig, TrackConfig) and file loading
│   ├── parser.py          # BeReal memories.json parsing, sorting, filtering, and GPS extraction
│   ├── geocoder.py        # Offline reverse-geocoding (lat/lon -> City, Country) with JSON caching
│   ├── compositor.py      # Pillow image composition (PIP rounding, border, text overlays, layout)
│   ├── audio.py           # Beat timeline computation and audio concatenation
│   └── video.py           # Zero-RAM FFmpeg video streaming, H.264 CRF 25 encoding, and metadata tagging
├── main.py                # CLI entry point (`-c / --config <path>`)
├── pyproject.toml         # Project metadata and dependencies (managed with uv)
├── uv.lock                # Locked dependency tree
├── AGENTS.md              # Guidelines for AI agents (this file)
└── README.md              # User documentation and setup guide
```

---

## 🛠️ Development & Tooling Guidelines

- **Package & Environment Manager**: Use `uv` for dependency management (`uv run`, `uv add`, `uv sync`).
- **Python Version**: Python 3.12+ (Python 3.14 compatible).
- **Key Dependencies**:
  - `Pillow` / `pilmoji`: High-performance 2D image composition, rounded rectangle masking, and emoji font rendering.
  - `imageio-ffmpeg`: Direct raw RGB frame streaming into FFmpeg subprocess ($O(1)$ RAM usage).
  - `soundfile` / `librosa` / `numpy`: Audio splicing, resampling, and timeline synchronization.
  - `reverse_geocoder`: Fast offline reverse geocoding from GPS coordinates to city/country.
  - `pydantic`: Type-safe configuration and input validation.
- **Git Discipline**:
  - Never commit raw personal data or images from `data/` or `songs/`.
  - Always verify `.gitignore` excludes `data/`, `songs/`, `output/`, and `*:Zone.Identifier`.

---

## 🎨 Layout & Rendering Specs

- **Canvas Size**: 1080 x 1920 pixels (9:16 aspect ratio).
- **Background Frame**: Scaled with center-crop to fit 1080x1920 without stretching.
- **Selfie PIP Frame**:
  - Width: ~28-30% of canvas width (~300-320px).
  - Position: Top-left with margin (`x=40, y=40`).
  - Corner Radius: ~24px with a 3px clean white border.
- **Text Overlays**:
  - Date & Location: Top-right aligned, white sans-serif text with soft drop shadow.
  - Caption: Bottom-centered, dynamic font scaling based on text length with word wrapping.
- **Encoding**: H.264 (`libx264`), `medium` preset, `crf=25`, `yuv420p` for optimal compression and universal compatibility.
