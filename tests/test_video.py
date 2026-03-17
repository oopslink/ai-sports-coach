import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.video import extract_frames, FrameExtractionError


def test_raises_if_video_not_found(tmp_path):
    with pytest.raises(FrameExtractionError, match="not found"):
        extract_frames(Path("/nonexistent/video.mp4"), tmp_path)


def test_raises_if_ffmpeg_not_installed(tmp_path, mocker):
    mocker.patch("src.video.shutil.which", return_value=None)
    fake_video = tmp_path / "video.mp4"
    fake_video.touch()
    with pytest.raises(FrameExtractionError, match="ffmpeg"):
        extract_frames(fake_video, tmp_path)


def test_returns_12_frame_paths(tmp_path, mocker):
    mocker.patch("src.video.shutil.which", return_value="/usr/bin/ffmpeg")
    # Use a real path that exists (tmp_path itself) as the video to bypass the existence check
    fake_video = tmp_path / "video.mp4"
    fake_video.touch()
    mock_run = mocker.patch("subprocess.run")
    # Use side_effect to return different results for ffprobe and ffmpeg calls
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="10.0\n"),  # ffprobe call
        MagicMock(returncode=0, stdout=""),         # ffmpeg call
    ]
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    # Simulate ffmpeg creating 12 frame files
    for i in range(1, 13):
        (frames_dir / f"frame_{i:03d}.jpg").touch()

    frames = extract_frames(fake_video, frames_dir)
    assert len(frames) == 12
    assert all(f.suffix == ".jpg" for f in frames)


def test_uses_fallback_when_ffprobe_fails(tmp_path, mocker):
    mocker.patch("src.video.shutil.which", return_value="/usr/bin/ffmpeg")
    fake_video = tmp_path / "video.mp4"
    fake_video.touch()
    mock_run = mocker.patch("subprocess.run")
    # Use side_effect: ffprobe fails, ffmpeg succeeds
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout=""),         # ffprobe call fails
        MagicMock(returncode=0, stdout=""),         # ffmpeg call succeeds
    ]
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    # Pre-create 12 frame files that ffmpeg would have created
    for i in range(1, 13):
        (frames_dir / f"frame_{i:03d}.jpg").touch()

    frames = extract_frames(fake_video, frames_dir)
    assert len(frames) == 12
    assert all(f.suffix == ".jpg" for f in frames)
