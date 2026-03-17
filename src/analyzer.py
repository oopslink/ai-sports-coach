import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import openai


class AnalyzerError(Exception):
    pass


@dataclass
class AnalysisResult:
    sport: str
    score: int
    strengths: list[str]
    issues: list[str]
    suggestions: list[str]
    summary: str


SYSTEM_PROMPT = """You are a professional sports coach with decades of experience analyzing athlete technique.
Analyze the provided video frames and background context, then respond ONLY with a JSON object using this exact schema:
{
  "sport": "<detected sport>",
  "score": <integer 0-10>,
  "strengths": ["<observed strength>", ...],
  "issues": ["<technique problem with frame reference>", ...],
  "suggestions": ["<prioritized improvement>", ...],
  "summary": "<narrative paragraph>"
}
Be specific, reference frame numbers where relevant, and give actionable coaching advice."""


def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def analyze_frames(frames: list[Path], context: str, api_key: Optional[str] = None) -> AnalysisResult:
    """Send frames to GPT-4o Vision and return structured analysis."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise AnalyzerError(
            "OPENAI_API_KEY is not set. Add it to your .env file:\n  OPENAI_API_KEY=sk-..."
        )

    client = openai.OpenAI(api_key=key)

    content: list[dict] = [
        {"type": "text", "text": f"Athlete background: {context}\n\nAnalyze the following {len(frames)} frames:"}
    ]
    for i, frame in enumerate(frames, 1):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{_encode_image(frame)}",
                "detail": "low",
            },
        })
        content.append({"type": "text", "text": f"[Frame {i}]"})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=1500,
        )
    except openai.OpenAIError as e:
        raise AnalyzerError(f"OpenAI API error: {e}") from e

    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON block if wrapped in markdown
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            raise AnalyzerError(f"Failed to parse API response as JSON:\n{raw}")

    return AnalysisResult(
        sport=data.get("sport", "unknown"),
        score=int(data.get("score", 0)),
        strengths=data.get("strengths", []),
        issues=data.get("issues", []),
        suggestions=data.get("suggestions", []),
        summary=data.get("summary", ""),
    )
