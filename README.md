# 📸 BeReal Year Recap Generator (`be_recap`)

Transform your exported **BeReal** memories from any year into a fast-paced, music-synced vertical recap video (9:16 format) — displaying **1 memory per musical beat**.

---

## ✨ Features

- 🎵 **Beat-Synced Transitions**: Syncs BeReal photos to 1 or 2 background tracks based on precise BPM timings.
- 📱 **True BeReal Look & Feel**:
  - Full-screen back camera portrait/scenery photo.
  - Picture-in-picture (PIP) front camera selfie in the top-left corner with rounded corners and a clean border.
  - Top-right overlay with formatted date (`DD.MM.YYYY`) and reverse-geocoded location (`City, Country`).
  - Bottom caption banner with **adaptive font sizing** to automatically fit short and long captions cleanly.
- 🔄 **Multi-Track Support**: Seamlessly sequence 1–2 songs with their respective BPMs to cover all memories across the year.
- ⚡ **Fast & Offline**: Uses offline reverse geocoding for GPS coordinates and hardware-accelerated FFmpeg/MoviePy rendering.

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.12+ (or 3.14)
- [`uv`](https://docs.astral.sh/uv/) package manager (recommended) or `pip`
- `ffmpeg` installed on your system

### 2. Installation

Clone this repository and install dependencies using `uv`:

```bash
git clone <repo-url> be_recap
cd be_recap
uv sync
```

### 3. Add Your BeReal Data

1. Request your data export from the BeReal mobile app (**Settings → Account → Help & Feedback → Contact Us / Download My Data**).
2. Extract the downloaded zip folder into the `data/` directory. The structure will look like:
   ```
   data/
   └── <export-folder>/
       ├── memories.json
       ├── posts.json
       └── Photos/
           └── post/
               ├── *.webp
               └── ...
   ```
   *(Note: `data/` is strictly ignored by `.gitignore` to protect your privacy).*

### 4. Configure & Run

Configure your target year and music tracks in `main.py` (or CLI arguments):

```python
SELECTED_YEAR = 2025

# 1-2 Songs with their BPM
TRACKS = [
    {"path": "data/song1.mp3", "bpm": 128},
    {"path": "data/song2.mp3", "bpm": 120},
]
```

Run the generator:

```bash
uv run python main.py
```

The output video will be rendered as `bereal_recap_<YEAR>.mp4`.

---

## 🛠️ Project Structure

```
be_recap/
├── data/              # Local data (BeReal export archive & audio tracks, git-ignored)
├── src/
│   ├── config.py      # Project settings & schema definitions
│   ├── parser.py      # Data extraction & filtering for memories.json
│   ├── geocoder.py    # Offline coordinate-to-city lookup
│   ├── compositor.py  # Pillow image compositing (PIP, rounded corners, text layout)
│   ├── audio.py       # Beat timeline & audio splicing
│   └── video.py       # Final video assembly & rendering
├── main.py            # Main execution script
├── AGENTS.md          # Guide for AI coding assistants
├── pyproject.toml     # Project metadata and dependencies
└── README.md          # This documentation
```

---

## 📄 License

MIT License
