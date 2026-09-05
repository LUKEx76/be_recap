import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class TrackConfig(BaseModel):
    """Configuration for an individual audio track."""
    path: Path
    bpm: float = Field(..., gt=0, description="Beats per minute of the track")
    start_offset_seconds: float = Field(default=0.0, ge=0.0, description="Offset in seconds from which to start the track")

    @field_validator("path")
    @classmethod
    def validate_track_path(cls, v: Path) -> Path:
        resolved = Path(v).expanduser().resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Audio track file does not exist: {resolved}")
        return resolved


class AppConfig(BaseModel):
    """Configuration schema for BeReal recap video generation."""
    year: int = Field(..., ge=2000, le=2100, description="Target year for recap")
    export_dir: Path = Field(..., description="Directory of the extracted BeReal archive")
    tracks: List[TrackConfig] = Field(..., min_length=1, description="List of 1 or more audio tracks")
    output_path: Path = Field(default=Path("bereal_recap.mp4"), description="Output video file path")
    fps: int = Field(default=30, gt=0, le=120, description="Video frames per second")
    width: int = Field(default=1080, gt=0, description="Video width in pixels (default 1080)")
    height: int = Field(default=1920, gt=0, description="Video height in pixels (default 1920)")
    date_format: str = Field(default="%d.%m.%Y", description="Date display format")

    @field_validator("export_dir")
    @classmethod
    def validate_export_dir(cls, v: Path) -> Path:
        resolved = Path(v).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise FileNotFoundError(f"BeReal export directory does not exist: {resolved}")
        memories_file = resolved / "memories.json"
        if not memories_file.exists():
            raise FileNotFoundError(f"Missing required 'memories.json' in export directory: {memories_file}")
        photos_dir = resolved / "Photos" / "post"
        if not photos_dir.exists():
            raise FileNotFoundError(f"Missing required 'Photos/post' directory in export directory: {photos_dir}")
        return resolved

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: Path) -> Path:
        resolved = Path(v).expanduser().resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    @classmethod
    def load_from_file(cls, config_path: str | Path) -> "AppConfig":
        """Load and validate configuration from a JSON file."""
        cfg_file = Path(config_path).expanduser().resolve()
        if not cfg_file.exists() or not cfg_file.is_file():
            raise FileNotFoundError(f"Configuration file does not exist: {cfg_file}")
        
        with open(cfg_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in configuration file '{cfg_file}': {e}") from e
                
        return cls.model_validate(data)
