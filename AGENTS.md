# AGENTS.md — AI Agent Guide for `be_recap`

Welcome to **be_recap**, a Python-based multimedia processing pipeline designed to generate vertical BeReal year-in-review recap videos synced to audio BPM.

---

## 🎯 Project Objective

Generate high-quality 9:16 vertical recap videos from an exported BeReal archive for any selected year:
1. **Beat Syncing**: Display exactly 1 BeReal memory per beat based on user-provided music tracks (1–2 songs) and BPMs.
2. **Authentic BeReal Layout**:
   - **Background**: Large full-frame primary/back camera photo (scaled and centered).
   - **Top-Left PIP**: Front-facing selfie camera photo with rounded corners and a subtle white border.
   - **Top-Right Overlay**: Date (`DD.MM.YYYY`) and Location (`City, Country` via reverse geocoding).
   - **Bottom Overlay**: Caption with adaptive font sizing to prevent overflow and ensure legibility.
3. **Sequential Audio Chaining**: Support 1 or 2 sequential audio tracks, smoothly transitioning audio and timing.

---

## 🏗️ Architecture & Modules

The project follows a clean, modular structure:

```
be_recap/
├── data/                  # Git-ignored local BeReal export folders and audio tracks
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration dataclass / Pydantic (year, songs, BPM, visual styling)
│   ├── parser.py          # BeReal memories.json parsing, sorting, filtering, and GPS extraction
│   ├── geocoder.py        # Offline reverse-geocoding (lat/lon -> City, Country) with caching
│   ├── compositor.py      # Pillow / OpenCV image frame generation (PIP rounding, text overlays, layout)
│   ├── audio.py           # Beat timeline computation and audio concatenation
│   └── video.py           # MoviePy / FFmpeg video assembly and rendering
├── main.py                # CLI entry point to run generation
├── pyproject.toml         # Project metadata and dependencies (managed with uv)
├── uv.lock                # Locked dependency tree
├── AGENTS.md              # Guidelines for AI agents (this file)
└── README.md              # User documentation and setup guide
```

---

## 🛠️ Development & Tooling Guidelines

- **Package & Environment Manager**: Use `uv` for dependency management (`uv run`, `uv add`, `uv sync`).
- **Python Version**: Python 3.12+ (or 3.14 compatible).
- **Key Dependencies**:
  - `moviepy` (>=2.0): Video compilation and audio/video muxing.
  - `Pillow` / `opencv-python`: High-performance 2D image composition, rounded rectangle masking, text rendering.
  - `reverse_geocoder`: Fast offline reverse geocoding from GPS coordinates to city/country.
  - `pydantic`: Type-safe configuration and input validation.
  - `soundfile` / `librosa`: Audio processing and timeline calculation.
- **Git Discipline**:
  - Never commit raw personal data or images from `data/`.
  - Always verify `.gitignore` excludes `data/` and `*:Zone.Identifier`.

---

## 🎨 Layout & Rendering Specs

- **Canvas Size**: 1080 x 1920 pixels (9:16 aspect ratio).
- **Background Frame**: Scaled with center-crop to fit 1080x1920 without stretching.
- **Selfie PIP Frame**:
  - Width: ~28-30% of canvas width (~300-320px).
  - Position: Top-left with margin (e.g. `x=40, y=40`).
  - Corner Radius: ~24px with a 3px clean white border.
- **Text Overlays**:
  - Date & Location: Top-right aligned, white sans-serif text with soft drop shadow or semi-transparent backing.
  - Caption: Bottom-centered, dynamic font scaling based on text length with wrapping.
