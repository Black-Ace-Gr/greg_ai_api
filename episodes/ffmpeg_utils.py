"""
FFmpeg-based assembly: turns one panel's image + audio + optional caption
into a short video clip with a subtle pan/zoom (Ken Burns) effect, then
concatenates every clip in an episode into the final motion comic.

Pure local CPU work - no GPU, no paid API, no network. Safe to run and
iterate on for free before any real image/voice generation exists (see
mock/generate_placeholder_assets.py for how this gets tested standalone).
"""

import json
import subprocess
from pathlib import Path

# Output video settings - tweak freely, these don't affect generation cost.
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS = 30
ZOOM_AMOUNT = 1.08  # how much the image zooms in over the clip's duration


def probe_duration_seconds(media_path: Path) -> float:
    """Read a media file's duration via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(media_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _escape_drawtext(text: str) -> str:
    """Escape text for ffmpeg's drawtext filter."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\u2019")  # avoid quote-escaping headaches entirely
    )


def render_panel_clip(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    caption_text: str | None = None,
) -> Path:
    """
    Render one clip: a still image with a slow pan/zoom, the given audio
    track laid under it, and an optional caption burned in at the bottom
    (used for dialogue lines - narration has no caption).

    Clip duration is driven by the audio's length, so pacing follows what
    was actually said/narrated.
    """
    duration = probe_duration_seconds(audio_path)
    total_frames = max(1, int(duration * FPS))

    # zoompan needs a slightly oversized source so it has room to zoom into.
    zoompan = (
        f"scale={FRAME_WIDTH * 2}:{FRAME_HEIGHT * 2},"
        f"zoompan=z='min(zoom+{(ZOOM_AMOUNT - 1) / total_frames:.8f},{ZOOM_AMOUNT})':"
        f"d={total_frames}:s={FRAME_WIDTH}x{FRAME_HEIGHT}:fps={FPS}"
    )

    filter_chain = zoompan
    if caption_text:
        safe_text = _escape_drawtext(caption_text)
        filter_chain += (
            ",drawtext=text='" + safe_text + "'"
            ":fontcolor=white:fontsize=36:box=1:boxcolor=black@0.55:boxborderw=14"
            ":x=(w-text_w)/2:y=h-th-40"
        )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-filter:v", filter_chain,
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path


def concatenate_clips(clip_paths: list[Path], output_path: Path) -> Path:
    """Concatenate already-rendered clips (same codec/resolution) into one file."""
    concat_list_path = output_path.parent / f"{output_path.stem}_concat_list.txt"
    with open(concat_list_path, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
        "-c", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    concat_list_path.unlink(missing_ok=True)
    return output_path
