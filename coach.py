#!/usr/bin/env python3
"""AI Sports Coach Analyzer — CLI entry point."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.video import extract_frames, FrameExtractionError
from src.analyzer import analyze_frames, AnalyzerError
from src.search import fetch_reference_images
from src.report import generate_report

load_dotenv()


def get_context(args: argparse.Namespace) -> str:
    if args.context:
        return args.context
    if args.context_file:
        p = Path(args.context_file)
        if not p.exists():
            print(f"Error: context file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p.read_text(encoding="utf-8").strip()
    # Interactive fallback
    print("No background context provided.")
    print("Please describe the athlete (sport, level, goals):")
    return input("> ").strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Sports Coach: analyze a sports video with GPT-4o Vision"
    )
    parser.add_argument("--video", required=True, help="Path to the local video file")
    parser.add_argument("--context", help="Background description (inline string)")
    parser.add_argument("--context-file", help="Path to a text file with background description")
    parser.add_argument(
        "--output-dir", default="output", help="Directory to save report and images (default: output/)"
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    if video_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        print(f"Error: unsupported video format '{video_path.suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}", file=sys.stderr)
        sys.exit(1)

    context = get_context(args)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = output_dir / "frames"
    print(f"Extracting frames from {video_path}...")
    try:
        frames = extract_frames(video_path, frames_dir)
    except FrameExtractionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  → {len(frames)} frames extracted to {frames_dir}")

    api_key = os.getenv("OPENAI_API_KEY")
    print("Analyzing with GPT-4o Vision...")
    try:
        result = analyze_frames(frames, context, api_key=api_key)
    except AnalyzerError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  → Sport detected: {result.sport}, Score: {result.score}/10")

    refs_dir = output_dir / "references"
    print(f"Searching for '{result.sport}' reference images...")
    references = fetch_reference_images(result.sport, refs_dir)
    print(f"  → {len(references)} reference image(s) downloaded")

    print("Generating Markdown report...")
    report_path = generate_report(
        result=result,
        context=context,
        frames=frames,
        references=references,
        output_dir=output_dir,
    )
    print(f"\nDone! Report saved to: {report_path}")


if __name__ == "__main__":
    main()
