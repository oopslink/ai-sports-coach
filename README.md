# AI Sports Coach

AI-powered sports video analysis system. Upload a training video, get professional coaching feedback with annotated frame images and structured reports.

## Supported Sports

| 运动 | Skill | Annotate Script | 标签数 |
|------|-------|----------------|--------|
| 室内攀岩 Indoor Climbing | `indoor-climbing-coach` | `climbing_annotate.py` | 10 |
| 网球 Tennis | `tennis-coach` | `tennis_annotate.py` | 21 |
| 乒乓球 Table Tennis | `tabletennis-coach` | `tabletennis_annotate.py` | 21 |
| 羽毛球 Badminton | `badminton-coach` | `badminton_annotate.py` | 21 |
| 足球 Football/Soccer | `football-coach` | `football_annotate.py` | 21 |
| 篮球 Basketball | `basketball-coach` | `basketball_annotate.py` | 21 |
| 排球 Volleyball | `volleyball-coach` | `volleyball_annotate.py` | 21 |

## How It Works

Every analysis runs in **3 steps**:

```
Step 1  coach.py               → extract frames + GPT-4o vision analysis → output/<sport>/coach_*.md
Step 2  <sport>_annotate.py    → annotate each frame with body-part circles + issue labels
Step 3  Claude Code skill      → output structured coaching report to user
```

Optional Step 4 — generate a PowerPoint deck:
```
node output/<sport>/gen_ppt.js
```

## Setup

**Requirements:** Python 3.11+, Node.js 18+, ffmpeg

```bash
# Install Python deps
pip install -r requirements.txt

# Install pptxgenjs (for PPT generation)
npm install -g pptxgenjs

# Install ffmpeg (macOS)
brew install ffmpeg

# Set your OpenAI API key
echo "OPENAI_API_KEY=sk-..." > .env
```

## Usage

### Step 1 — Analyze a video

```bash
python3 coach.py \
  --video "sample/tennis.mp4" \
  --output-dir "output/tennis" \
  --context "这是一段网球训练视频。请用中文进行专业网球教练分析。"
```

**Arguments:**

| Flag | Required | Description |
|------|----------|-------------|
| `--video` | ✅ | Path to video file (mp4 / mov / avi / mkv / webm) |
| `--output-dir` | — | Output directory (default: `output/`) |
| `--context` | — | Inline coaching context string |
| `--context-file` | — | Path to a `.txt` file with coaching context |

Output: `output/<sport>/frames/frame_*.jpg` + `output/<sport>/coach_*.md`

### Step 2 — Annotate frames

```bash
python3 tennis_annotate.py      # tennis
python3 tabletennis_annotate.py # table tennis
python3 badminton_annotate.py   # badminton
python3 football_annotate.py    # football / soccer
python3 basketball_annotate.py  # basketball
python3 volleyball_annotate.py  # volleyball
python3 climbing_annotate.py    # indoor climbing
```

Each script reads frames from `output/<sport>/frames/`, calls GPT-4o to classify technique issues, draws labeled circles on each frame, and writes:
- `output/<sport>/annotated/frame_*.jpg` — annotated images
- `output/<sport>/annotate_*.md` — per-frame issue report

### Step 3 — Generate PPT (optional)

```bash
node output/tennis/gen_ppt.js
```

Produces `output/tennis/report.pptx` — a 12-page coaching deck with score overview, per-issue deep-dive pages, training plans, and coach summary.

## Output Directory Structure

```
output/
├── climbing/
│   ├── frames/          # raw extracted frames
│   ├── annotated/       # annotated frames (body-part circles + labels)
│   ├── coach_*.md       # GPT-4o coaching report (Step 1)
│   ├── annotate_*.md    # per-frame annotation report (Step 2)
│   ├── gen_ppt.js       # PPT generator
│   └── report.pptx      # generated deck
├── tennis/
├── tabletennis/
├── badminton/
├── football/
├── basketball/
└── volleyball/
```

## Annotation Legend

Each annotated frame uses a consistent color scheme:

| Color | Meaning |
|-------|---------|
| 🔵 Blue circle | Body center of mass |
| 🟢 Green circle | Dominant hand / racket hand |
| 🟢 Dark green circle | Off hand |
| 🟠 Orange circle | Lead foot |
| 🟠 Dark orange circle | Back foot |
| 🔴 Red outer ring | Body part with technique issue |
| 🟢 Green outer ring | Body part with correct technique (positive) |
| Black+yellow text | Issue label (English) |

## Issue Labels

Each sport has **21 classified issue types** organized by category. Examples:

**Tennis:** `LATE BACKSWING` · `WRONG CONTACT` · `NO SPLIT STEP` · `LATE WEIGHT` · `BAD TOSS` · `TELEGRAPH` · `GOOD FORM`

**Badminton:** `LATE FOOTWORK` · `NO SPLIT STEP` · `LATE LUNGE` · `NO WRIST SNAP` · `FLAT CLEAR` · `HAIRPIN ERROR` · `NO JUMP SMASH` · `GOOD DECEPTION`

**Basketball:** `FLAT ARC` · `ELBOW FLARE` · `LATE RELEASE` · `NO LEG BEND` · `OVER DRIBBLE` · `NO BOX OUT` · `NO BALL DENIAL` · `GOOD DEFENSE`

**Volleyball:** `WRONG PLATFORM` · `WRONG DIG ANG` · `LATE SET HANDS` · `NO WRIST SNAP` · `BAD JUMP TIMING` · `NO PENETRATION` · `POOR RECEPTION` · `GOOD SET`

Full label tables are in each sport's skill file under `.claude/skills/<sport>-coach/skill.md`.

## Using with Claude Code

This project ships with Claude Code skills for each sport. In a Claude Code session, just describe your video:

```
分析下这段网球视频 sample/tennis.mp4
```

Claude will automatically invoke the correct skill and run the full 3-step pipeline.

## GPT-4o Notes

- System prompt must be **English** (Chinese prompts trigger content refusals)
- Do not use language that implies person identification; use `biomechanics analysis`
- Use `detail=low` for frame batches (12 frames with `detail=high` is often filtered)
- System prompt must declare: `"<sport> training footage for technique improvement"`

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Video file not found` | Check the path; supported formats: mp4 mov avi mkv webm |
| `ffmpeg is not installed` | `brew install ffmpeg` |
| `OPENAI_API_KEY is not set` | Create `.env` with `OPENAI_API_KEY=sk-...` |
| GPT-4o refuses to analyze images | Check system prompt is English with no identity-language |
| `output/<sport>/frames/` is empty | Run `coach.py` first before running the annotate script |
| `Cannot find module 'pptxgenjs'` | Use full path: `require("/opt/homebrew/lib/node_modules/pptxgenjs")` |
