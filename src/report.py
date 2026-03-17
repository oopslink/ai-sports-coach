from datetime import datetime
from pathlib import Path

from src.analyzer import AnalysisResult


def generate_report(
    result: AnalysisResult,
    context: str,
    frames: list[Path],
    references: list[Path],
    output_dir: Path,
) -> Path:
    """Assemble and save a Markdown coach analysis report."""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"report_{timestamp}.md"

    lines: list[str] = []

    # Header
    date_str = now.strftime("%Y-%m-%d")
    lines += [
        f"# Coach Analysis: {result.sport} — {date_str}",
        "",
        "## Background",
        "",
        "\n".join(f"> {line}" for line in context.splitlines()),
        "",
    ]

    # Key Frames
    lines += ["## Key Frames", ""]
    for frame in frames:
        rel = frame.relative_to(output_dir) if frame.is_relative_to(output_dir) else frame
        lines.append(f"![{frame.stem}]({rel})")
    lines.append("")

    # Analysis
    lines += [
        "## Analysis",
        "",
        f"### Overall Score: {result.score}/10",
        "",
        "## Strengths",
        "",
    ]
    for s in result.strengths:
        lines.append(f"- {s}")
    lines.append("")

    lines += ["## Issues Found", ""]
    for issue in result.issues:
        lines.append(f"- {issue}")
    lines.append("")

    lines += ["## Improvement Suggestions", ""]
    for i, suggestion in enumerate(result.suggestions, 1):
        lines.append(f"{i}. {suggestion}")
    lines.append("")

    lines += ["## Coach Summary", "", result.summary, ""]

    # Reference images (optional)
    if references:
        lines += ["## Standard Reference", ""]
        for ref in references:
            rel = ref.relative_to(output_dir) if ref.is_relative_to(output_dir) else ref
            lines.append(f"![Reference: {ref.stem}]({rel})")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
