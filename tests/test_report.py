import pytest
from pathlib import Path
from datetime import date
from src.analyzer import AnalysisResult
from src.report import generate_report


MOCK_RESULT = AnalysisResult(
    sport="tennis",
    score=7,
    strengths=["Good stance", "Consistent toss"],
    issues=["Elbow too low on backswing (frame 3)"],
    suggestions=["Keep elbow at shoulder height"],
    summary="Overall solid technique with room to improve power generation.",
)


def test_report_file_is_created(tmp_path):
    frames = [tmp_path / f"frame_{i:03d}.jpg" for i in range(1, 4)]
    for f in frames:
        f.touch()
    references = [tmp_path / "ref_001.jpg"]
    references[0].touch()

    report_path = generate_report(
        result=MOCK_RESULT,
        context="I am a beginner",
        frames=frames,
        references=references,
        output_dir=tmp_path,
    )

    assert report_path.exists()
    assert report_path.suffix == ".md"


def test_report_contains_key_sections(tmp_path):
    frames = [tmp_path / f"frame_{i:03d}.jpg" for i in range(1, 4)]
    for f in frames:
        f.touch()

    report_path = generate_report(
        result=MOCK_RESULT,
        context="I am a beginner",
        frames=frames,
        references=[],
        output_dir=tmp_path,
    )

    content = report_path.read_text()
    assert "# Coach Analysis: tennis" in content
    assert "## Background" in content
    assert "## Key Frames" in content
    assert "Overall Score: 7/10" in content
    assert "## Strengths" in content
    assert "## Issues Found" in content
    assert "## Improvement Suggestions" in content
    assert "## Coach Summary" in content
    assert "Good stance" in content
    assert "Keep elbow at shoulder height" in content


def test_report_skips_reference_section_when_empty(tmp_path):
    frames = [tmp_path / "frame_001.jpg"]
    frames[0].touch()

    report_path = generate_report(
        result=MOCK_RESULT,
        context="context",
        frames=frames,
        references=[],
        output_dir=tmp_path,
    )

    content = report_path.read_text()
    assert "## Standard Reference" not in content


def test_report_includes_reference_section_when_present(tmp_path):
    frames = [tmp_path / "frame_001.jpg"]
    frames[0].touch()
    ref = tmp_path / "ref_001.jpg"
    ref.touch()

    report_path = generate_report(
        result=MOCK_RESULT,
        context="context",
        frames=frames,
        references=[ref],
        output_dir=tmp_path,
    )

    content = report_path.read_text()
    assert "## Standard Reference" in content
    assert "ref_001.jpg" in content
