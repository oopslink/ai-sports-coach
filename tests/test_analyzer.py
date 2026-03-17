import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.analyzer import analyze_frames, AnalysisResult, AnalyzerError


MOCK_RESPONSE = {
    "sport": "tennis",
    "score": 7,
    "strengths": ["Good stance", "Consistent toss"],
    "issues": ["Elbow too low on backswing (frame 3)", "Weight not transferring (frame 8)"],
    "suggestions": ["Keep elbow at shoulder height during backswing", "Step into the ball"],
    "summary": "Overall solid technique with room to improve power generation."
}


def test_raises_if_no_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AnalyzerError, match="OPENAI_API_KEY"):
        analyze_frames([], "context", api_key=None)


def test_returns_analysis_result(tmp_path, mocker):
    # Create a tiny 1x1 JPEG for testing
    frame = tmp_path / "frame_001.jpg"
    frame.write_bytes(
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e\xc0'
        b'\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00'
        b'\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01'
        b'\x01\x00\x00?\x00\xf5\x0f\xff\xd9'
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps(MOCK_RESPONSE)))]
    )
    mocker.patch("src.analyzer.openai.OpenAI", return_value=mock_client)

    result = analyze_frames([frame], "I am a beginner tennis player", api_key="sk-test")

    assert isinstance(result, AnalysisResult)
    assert result.sport == "tennis"
    assert result.score == 7
    assert len(result.strengths) == 2
    assert len(result.issues) == 2
    assert len(result.suggestions) == 2
    assert result.summary != ""


def test_raises_on_invalid_json_response(tmp_path, mocker):
    frame = tmp_path / "frame_001.jpg"
    frame.write_bytes(b'\xff\xd8\xff\xd9')  # minimal JPEG

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="not json at all"))]
    )
    mocker.patch("src.analyzer.openai.OpenAI", return_value=mock_client)

    with pytest.raises(AnalyzerError, match="Failed to parse"):
        analyze_frames([frame], "context", api_key="sk-test")


def test_handles_markdown_wrapped_json_response(tmp_path, mocker):
    frame = tmp_path / "frame_001.jpg"
    frame.write_bytes(b'\xff\xd8\xff\xd9')

    mock_client = MagicMock()
    # GPT-4o sometimes wraps JSON in markdown code fences
    wrapped = f"```json\n{json.dumps(MOCK_RESPONSE)}\n```"
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=wrapped))]
    )
    mocker.patch("src.analyzer.openai.OpenAI", return_value=mock_client)

    result = analyze_frames([frame], "context", api_key="sk-test")
    assert result.sport == "tennis"
    assert result.score == 7
