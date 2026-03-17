import shutil
import subprocess
from pathlib import Path


class FrameExtractionError(Exception):
    pass


# Extract every Nth frame where N is the frame skip interval
FALLBACK_FRAME_SKIP_INTERVAL = 10


def extract_frames(video_path: Path, output_dir: Path, num_frames: int = 12) -> list[Path]:
    """Extract num_frames evenly spaced frames from video_path into output_dir."""
    if not video_path.exists():
        raise FrameExtractionError(f"Video file not found: {video_path}")

    if shutil.which("ffmpeg") is None:
        raise FrameExtractionError(
            "ffmpeg is not installed. Install it with: brew install ffmpeg (macOS) "
            "or apt install ffmpeg (Linux)"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%03d.jpg")

    # Use fps filter to extract evenly spaced frames
    # Get video duration first, then compute fps to yield num_frames
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
        ],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip()) if probe.returncode == 0 and probe.stdout.strip() else None

    if duration:
        fps = num_frames / duration
        vf_filter = f"fps={fps:.6f}"
    else:
        # Fallback: extract every Nth frame when duration cannot be determined
        vf_filter = f"select='not(mod(n\\,{FALLBACK_FRAME_SKIP_INTERVAL}))',setpts=N/FRAME_RATE/TB"

    result = subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-vf", vf_filter,
         "-frames:v", str(num_frames), "-q:v", "2", output_pattern, "-y"],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        raise FrameExtractionError(f"ffmpeg failed:\n{result.stderr}")

    frames = sorted(output_dir.glob("frame_*.jpg"))

    # Validate frame count: allow more frames (ffmpeg sometimes extracts one extra),
    # but raise error if fewer than expected frames were extracted
    if len(frames) < num_frames:
        raise FrameExtractionError(f"Expected {num_frames} frames but got {len(frames)}")

    return frames
