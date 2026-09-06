# 📸 BeReal Year Recap Generator (`be_recap`)

Transform your exported **BeReal** memories from any year into a fast-paced, music-synced vertical recap video (9:16 format) — displaying **1 memory per musical beat**.

---

## ✨ Features

- 🎵 **Beat-Synced Transitions**: Syncs BeReal photos to 1 or 2 background tracks with precise BPM calculations and per-track tempo adaptation.
- 📱 **True BeReal Look & Feel**:
  - Full-screen back camera portrait/scenery photo (scaled and center-cropped).
  - Picture-in-picture (PIP) front camera selfie in the top-left corner with rounded corners and a clean white border.
  - Top-right overlay with formatted date (`DD.MM.YYYY`) and offline reverse-geocoded location (`City, Country`).
  - Bottom caption banner with **adaptive font scaling** and emoji rendering via `pilmoji`.
- 🔄 **Multi-Track Support**: Sequence 1 or 2 songs with independent BPMs and beat multipliers (`beats_per_memory`) to cover all memories across the year.
- 📅 **Gallery & Timezone Aware**: Embeds metadata and modification times set to Dec 31 23:59:59 in your local timezone so the video naturally appears at the end of the target year in Google Photos, Apple Photos, and Android galleries.
- ⚡ **Lightweight & High Performance**:
  - Zero-RAM frame streaming directly into an FFmpeg subprocess ($O(1)$ memory footprint).
  - Optimized H.264 encoding with CRF 25 to achieve compact, shareable files (~30–70 MB for ~3 minutes) without sacrificing 1080x1920 Full HD quality.
  - Offline reverse geocoding with local caching (`.geo_cache.json`).

---

## 📥 How to Export Your BeReal Data

BeReal allows you to request an archive of all your memories through their GDPR/privacy data export feature.

1. **Open the BeReal mobile app** (iOS or Android).
2. Go to your **Profile** and tap the **Settings** menu (three dots or gear icon in the top right).
3. Tap **Help & Feedback** $\rightarrow$ **Contact Us** $\rightarrow$ **Download My Data** (or submit a data request).
4. Enter your email address and submit the request.
5. **Check your email**: BeReal will send a download link for a `.zip` archive (this can take from a few hours up to several days depending on server load).
6. **Extract the ZIP file** into your project's `data/` directory.

The extracted folder structure should look like this:

```
data/
└── 2026-06-06/gNuKFTLhZAMEqVyRlmIcLLrR2Av1-1vAqR7wyKySp0Ige7-Rs4/
    ├── memories.json
    ├── posts.json
    └── Photos/
        └── post/
            ├── *.webp
            └── ...
```

> [!NOTE]
> For more community context and troubleshooting regarding BeReal exports, check out the [Reddit tutorial on exporting BeReal memories](https://www.reddit.com/r/bereal_app/comments/19dl0yk/experiencetutorial_for_exporting_all_bereal/).
>
> *(The `data/` directory is excluded by `.gitignore` to keep your personal photos and data private).*

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.12+** (tested up to Python 3.14)
- **[`uv`](https://docs.astral.sh/uv/)** package manager (recommended) or `pip`
- **`ffmpeg`** installed on your system

### 2. Installation

Clone this repository and install dependencies with `uv`:

```bash
git clone https://github.com/lukex76/be_recap.git
cd be_recap
uv sync
```

---

## ⚙️ Configuration & Customization

Create a JSON configuration file for your recap video (see [`configs/config.example.json`](configs/config.example.json)):

```json
{
  "year": 2025,
  "export_dir": "data/2026-06-06/gNuKFTLhZAMEqVyRlmIcLLrR2Av1-1vAqR7wyKySp0Ige7-Rs4",
  "output_path": "output/be_recap_2025.mp4",
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "date_format": "%d.%m.%Y",
  "tracks": [
    {
      "path": "songs/first_song.mp3",
      "bpm": 106.0,
      "beats_per_memory": 1,
      "start_offset_seconds": 0.0
    },
    {
      "path": "songs/second_song.mp3",
      "bpm": 170.0,
      "beats_per_memory": 2,
      "start_offset_seconds": -0.35
    }
  ]
}
```

### Configuration Options

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `year` | `int` | *Required* | The target calendar year to include in the recap. |
| `export_dir` | `string` | *Required* | Path to the extracted BeReal archive folder containing `memories.json` and `Photos/post`. |
| `output_path` | `string` | `bereal_recap.mp4` | Destination path for the rendered MP4 video. |
| `fps` | `int` | `30` | Video frame rate (30 fps is recommended for smooth beat quantization). |
| `width` | `int` | `1080` | Canvas width in pixels (9:16 vertical format). |
| `height` | `int` | `1920` | Canvas height in pixels (9:16 vertical format). |
| `date_format` | `string` | `"%d.%m.%Y"` | Date overlay format string (e.g. `DD.MM.YYYY`). |
| `tracks` | `list` | *Required* | List of 1 or 2 audio tracks configured in sequence. |

### Track Options

- **`path`**: File path to the audio file (`.mp3`, `.wav`, `.m4a`, etc.).
- **`bpm`**: Beats per minute of the track (can be checked using sites like [songbpm.com](https://songbpm.com) or BPM counter tools).
- **`beats_per_memory`**: Number of beats each photo is shown for (`1` = 1 photo every beat, `2` = 1 photo every 2 beats for half-time).
- **`start_offset_seconds`**:
  - `> 0.0`: Trims the beginning of the audio track to skip intros.
  - `< 0.0`: Prepends silence / delays the track to align the musical downbeat with the first photo.

---

## 🎬 Generating Your Recap Video

Run the generator using your config file:

```bash
uv run python main.py -c configs/config_2025.json
```

The pipeline will:
1. Parse and filter your BeReal memories for the target year.
2. Reverse-geocode GPS coordinates into human-readable cities and countries.
3. Stitch and tempo-sync your audio tracks.
4. Render the video with intro & outro year cards and beat-accurate photo transitions.
5. Apply local timezone metadata tags so the recap sits at the end of the year in your gallery.

---

## 🛠️ Project Structure

```
be_recap/
├── configs/               # Example and user configuration JSONs
│   └── config.example.json
├── data/                  # Local BeReal export archives (git-ignored)
├── songs/                 # Local audio tracks (git-ignored)
├── src/
│   ├── __init__.py
│   ├── config.py          # Pydantic configuration schemas and validation
│   ├── parser.py          # BeReal memories.json parsing, sorting, and image validation
│   ├── geocoder.py        # Fast offline GPS reverse geocoding with JSON caching
│   ├── compositor.py      # Pillow image composition (PIP rounding, border, adaptive captions)
│   ├── audio.py           # Beat timeline computation and audio concatenation
│   └── video.py           # Zero-RAM FFmpeg video streaming and metadata handling
├── main.py                # CLI entry point
├── pyproject.toml         # Project metadata and dependencies (managed with uv)
├── uv.lock                # Locked dependency tree
├── AGENTS.md              # AI agent pair programming guidelines
└── README.md              # Project documentation
```

---

## 📄 License

MIT License. Feel free to use, modify, and share!
