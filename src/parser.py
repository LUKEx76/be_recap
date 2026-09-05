import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from src.geocoder import reverse_geocode


class MemoryItem(BaseModel):
    """Represent an individual BeReal memory."""
    date: datetime
    formatted_date: str
    caption: str
    location_name: str
    front_image_path: Path
    back_image_path: Path


def parse_memories(
    export_dir: Path,
    target_year: int,
    date_format: str = "%d.%m.%Y"
) -> List[MemoryItem]:
    """
    Parses memories.json from a BeReal export, validates image presence,
    filters by target year, and sorts chronologically.
    
    Fails fast if files are missing or no memories match the target year.
    """
    export_dir = Path(export_dir).resolve()
    memories_file = export_dir / "memories.json"
    photos_dir = export_dir / "Photos" / "post"
    
    if not memories_file.is_file():
        raise FileNotFoundError(f"memories.json not found: {memories_file}")
    if not photos_dir.is_dir():
        raise FileNotFoundError(f"Photos/post directory not found: {photos_dir}")
        
    with open(memories_file, "r", encoding="utf-8") as f:
        try:
            raw_memories = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode memories.json: {e}") from e

    if not isinstance(raw_memories, list):
        raise ValueError(f"Expected memories.json to contain a list of objects, got {type(raw_memories).__name__}")

    matched_items: List[MemoryItem] = []

    for idx, item in enumerate(raw_memories):
        # 1. Parse timestamp (prefer takenTime, fallback to date)
        ts_str = item.get("takenTime") or item.get("date")
        if not ts_str:
            raise ValueError(f"Memory #{idx} is missing both 'takenTime' and 'date' fields.")
        
        # Parse ISO-8601 string (e.g. 2025-06-12T16:50:34.352Z)
        try:
            # Handle trailing 'Z' for UTC
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp '{ts_str}' in memory #{idx}: {e}") from e

        # Filter by year
        if dt.year != target_year:
            continue

        # 2. Extract image paths
        front_obj = item.get("frontImage")
        back_obj = item.get("backImage")
        if not front_obj or "path" not in front_obj:
            raise ValueError(f"Memory #{idx} ({ts_str}) is missing 'frontImage.path'")
        if not back_obj or "path" not in back_obj:
            raise ValueError(f"Memory #{idx} ({ts_str}) is missing 'backImage.path'")

        front_filename = Path(front_obj["path"]).name
        back_filename = Path(back_obj["path"]).name

        front_path = photos_dir / front_filename
        back_path = photos_dir / back_filename

        if not front_path.is_file():
            raise FileNotFoundError(f"Selfie photo missing on disk: {front_path} (from memory #{idx})")
        if not back_path.is_file():
            raise FileNotFoundError(f"Main photo missing on disk: {back_path} (from memory #{idx})")

        # 3. Clean caption
        raw_caption = item.get("caption") or ""
        caption = str(raw_caption).strip().strip('"').strip("'").strip()

        # 4. Reverse geocode location
        loc_obj = item.get("location")
        lat = loc_obj.get("latitude") if isinstance(loc_obj, dict) else None
        lon = loc_obj.get("longitude") if isinstance(loc_obj, dict) else None
        location_name = reverse_geocode(lat, lon)

        formatted_date = dt.strftime(date_format)

        matched_items.append(
            MemoryItem(
                date=dt,
                formatted_date=formatted_date,
                caption=caption,
                location_name=location_name,
                front_image_path=front_path,
                back_image_path=back_path,
            )
        )

    if not matched_items:
        raise ValueError(
            f"No BeReal memories found for target year {target_year} in '{export_dir}'. "
            f"Total raw memories in archive: {len(raw_memories)}."
        )

    # Sort strictly chronologically
    matched_items.sort(key=lambda m: m.date)
    return matched_items
