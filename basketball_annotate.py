#!/usr/bin/env python3
"""
basketball_annotate.py — 篮球教练标注工具
1. 把所有帧一次性发给 GPT-4o，返回球员身体部位坐标 + 技术问题
2. 用 PIL 在每帧上标注：身体圆圈、手脚点位、问题区域（英文标签）
3. 生成含标注图片的逐动作分析 Markdown 报告
"""

import base64
import json
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path

import openai
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

# ── 路径配置 ──────────────────────────────────────────────────────────────────
FRAMES_DIR    = Path("output/basketball/frames")
ANNOTATED_DIR = Path("output/basketball/annotated")
REPORT_PATH   = Path(f"output/basketball/annotate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

# ── 颜色（PIL RGB）────────────────────────────────────────────────────────────
COLOR = {
    "body":         ( 30, 144, 255),   # 蓝 — 身体重心
    "hand_l":       ( 50, 200,  80),   # 绿 — 投篮手
    "hand_r":       ( 20, 160,  50),   # 深绿 — 辅助手
    "foot_l":       (255, 140,   0),   # 橙 — 前脚
    "foot_r":       (220, 100,   0),   # 深橙 — 后脚
    "issue_ring":   (255,  50,  50),   # 红 — 问题高亮外圈
    "good_ring":    ( 50, 220,  80),   # 绿 — 正确标注外圈
    "label_body":   ( 20, 100, 200),
    "label_hand":   ( 20, 130,  50),
    "label_foot":   (180,  90,   0),
    "label_fg":     (255, 255, 255),
    "issue_note_bg":(  0,   0,   0),
    "issue_note_fg":(255, 220,  80),
}

# ── 问题类型（英文标签）───────────────────────────────────────────────────────
ISSUE_LABELS = {
    # 投篮技术
    "flat_trajectory":       "FLAT ARC",
    "elbow_flare":           "ELBOW FLARE",
    "no_wrist_follow":       "NO WRIST FLIP",
    "late_release":          "LATE RELEASE",
    "off_balance_shot":      "OFF BALANCE",
    "no_leg_bend":           "NO LEG BEND",
    # 控球与运球
    "ball_watching":         "BALL WATCHING",
    "poor_ball_handle":      "POOR HANDLE",
    "over_dribble":          "OVER DRIBBLE",
    "no_weak_hand":          "WEAK HAND",
    # 步法与移动
    "poor_footwork":         "POOR FOOTWORK",
    "wrong_pivot":           "WRONG PIVOT",
    "late_closeout":         "LATE CLOSEOUT",
    # 防守
    "poor_def_stance":       "POOR DEF STANCE",
    "no_box_out":            "NO BOX OUT",
    "ball_denial_miss":      "NO BALL DENIAL",
    # 进攻战术
    "poor_drive_angle":      "POOR DRIVE ANG",
    "late_shot_fake":        "NO SHOT FAKE",
    # 正面
    "good_form":             "GOOD FORM",
    "good_movement":         "GOOD MOVEMENT",
    "good_defense":          "GOOD DEFENSE",
}

# ── GPT-4o System Prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a professional basketball coach analyzing training footage for technique improvement.
You will receive sequential video frames from the same basketball training session.

Your task is sports biomechanics analysis — describe player body part POSITIONS using spatial coordinates only.
Do NOT attempt to identify the person. Focus on shooting mechanics, footwork, and court movement.

For each frame, locate the player and their limbs:
- body: center of mass / torso center
- hand_l: shooting hand
- hand_r: guide hand (non-dominant)
- foot_l: front/lead foot
- foot_r: back foot

All positions as fractions of image width (x_pct) and height (y_pct), range 0.0-1.0.
Radius: body ~0.06, limbs ~0.03.

Classify technique issues using ONLY these types:
- flat_trajectory: shot arc too flat (below 45 degree angle), low probability
- elbow_flare: shooting elbow flaring out sideways, not aligned to basket
- no_wrist_follow: wrist not snapping forward (no backspin, no "goose neck")
- late_release: ball released at or below head height rather than peak of jump
- off_balance_shot: shooting off-balance, feet not set, body falling sideways
- no_leg_bend: insufficient knee bend on catch, no leg power loaded into shot
- ball_watching: looking down at ball while dribbling instead of seeing court
- poor_ball_handle: inconsistent dribble rhythm, ball bouncing off fingertips
- over_dribble: using multiple dribbles when one or a pass would be more effective
- no_weak_hand: not protecting ball with non-dribbling hand, exposed to steal
- poor_footwork: poor footwork on catch-and-shoot, jab step, or off-dribble pull-up
- wrong_pivot: illegal pivot (pivot foot lifts), or inefficient pivot technique
- late_closeout: closing out on shooter too slowly, giving open look
- poor_def_stance: defensive stance too upright, feet too narrow, knees straight
- no_box_out: not establishing position between opponent and basket for rebound
- ball_denial_miss: not denying passing lane for one pass away offensive player
- poor_drive_angle: driving at wrong angle to basket (straight into help defense)
- late_shot_fake: missing opportunity to use shot fake to draw foul or create space
- good_form: correct shooting/defensive technique — highlight positively
- good_movement: excellent court movement or off-ball cutting — highlight positively
- good_defense: aggressive, disciplined defensive positioning — highlight positively

issue_note and frame_summary MUST be in ENGLISH.
Player analysis in Chinese.

Respond ONLY with valid JSON:
{
  "frames": {
    "1": {
      "players": [
        {
          "id": "P1",
          "body":   {"x_pct": 0.50, "y_pct": 0.50, "radius_pct": 0.06},
          "hand_l": {"x_pct": 0.52, "y_pct": 0.30, "radius_pct": 0.03, "issue_type": "elbow_flare", "issue_note": "Elbow pointing outward at 45 degrees"},
          "hand_r": {"x_pct": 0.46, "y_pct": 0.35, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "foot_l": {"x_pct": 0.48, "y_pct": 0.72, "radius_pct": 0.03, "issue_type": "poor_footwork", "issue_note": "Feet not squared to basket"},
          "foot_r": {"x_pct": 0.55, "y_pct": 0.74, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "body_issue_type": "off_balance_shot",
          "body_issue_note": "Body falling left, not balanced at release"
        }
      ],
      "frame_summary": "Jump shot attempt, elbow flaring out, off balance."
    }
  },
  "player_analysis": {
    "P1": {
      "overall_rating": 6,
      "strengths": ["优点1", "优点2"],
      "issues": [{"frame": 2, "type": "elbow_flare", "body_part": "hand_l", "detail": "中文描述"}],
      "improvement": "训练建议（中文）"
    }
  },
  "session_summary": "整体评价（中文）",
  "overall_score": 6
}"""


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def call_gpt4o(frames: list[Path]) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)
    content: list[dict] = [
        {"type": "text", "text": f"Basketball training footage — {len(frames)} sequential frames for biomechanics analysis:"}
    ]
    for i, frame in enumerate(frames, 1):
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encode_image(frame)}", "detail": "low"},
        })
        content.append({"type": "text", "text": f"[Frame {i}]"})

    print("  → 发送帧到 GPT-4o（篮球技术分析）...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        max_tokens=4000,
    )

    raw = response.choices[0].message.content
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise RuntimeError(f"JSON 解析失败:\n{raw}")


# ── 绘制工具 ──────────────────────────────────────────────────────────────────

def get_font(size: int):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_label(draw, text, cx, cy, bg, fg, font, padding=3):
    """在 (cx, cy) 上方绘制带背景标签。"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x0, y0 = cx - tw // 2 - padding, cy - th - padding * 2 - 4
    x1, y1 = cx + tw // 2 + padding, cy - 4
    draw.rectangle([x0, y0, x1, y1], fill=bg)
    draw.text((x0 + padding, y0 + padding), text, font=font, fill=fg)


def draw_issue_note(draw, note, cx, cy, img_w, font):
    """在 (cx, cy) 下方绘制问题说明（英文，自动换行）。"""
    lines = textwrap.wrap(note, 16)[:2]
    y = cy + 38
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = max(4, min(cx - tw // 2, img_w - tw - 4))
        draw.rectangle([tx - 2, y - 1, tx + tw + 2, y + 15], fill=COLOR["issue_note_bg"] + (180,))
        draw.text((tx, y), line, font=font, fill=COLOR["issue_note_fg"])
        y += 16


def draw_part(draw, part_data, label, bg_color, img_w, img_h, font_label, font_note):
    """绘制单个身体部位（手/脚/身体）。"""
    if not part_data:
        return
    x_pct      = float(part_data.get("x_pct", 0))
    y_pct      = float(part_data.get("y_pct", 0))
    r_pct      = float(part_data.get("radius_pct", 0.03))
    issue_type = part_data.get("issue_type", "")
    issue_note = part_data.get("issue_note", "")

    cx = int(x_pct * img_w)
    cy = int(y_pct * img_h)
    r  = max(int(r_pct * img_w), 14)

    is_issue = issue_type and issue_type not in ("good_form", "good_movement")
    is_good  = issue_type in ("good_form", "good_movement")

    # 外圈
    if is_issue:
        draw.ellipse([cx-r-5, cy-r-5, cx+r+5, cy+r+5], outline=COLOR["issue_ring"]+(210,), width=3)
    elif is_good:
        draw.ellipse([cx-r-5, cy-r-5, cx+r+5, cy+r+5], outline=COLOR["good_ring"]+(210,), width=3)

    # 主圈
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=bg_color+(220,), width=2)

    # 标签
    tag = ISSUE_LABELS.get(issue_type, "")
    full_label = f"{label}" + (f" {tag}" if tag else "")
    draw_label(draw, full_label, cx, cy, bg=bg_color+(200,), fg=COLOR["label_fg"], font=font_label)

    # 问题说明
    if issue_note and is_issue:
        draw_issue_note(draw, issue_note, cx, cy, img_w, font_note)


def annotate_frame(frame_path: Path, players: list[dict], out_path: Path):
    img = Image.open(frame_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    W, H = img.size

    font_label = get_font(15)
    font_note  = get_font(12)

    for p in players:
        pid = p.get("id", "P1")

        # 身体（重心）
        body = p.get("body", {})
        body_issue = {"x_pct": body.get("x_pct", 0), "y_pct": body.get("y_pct", 0),
                      "radius_pct": body.get("radius_pct", 0.06),
                      "issue_type": p.get("body_issue_type", ""),
                      "issue_note": p.get("body_issue_note", "")}
        draw_part(draw, body_issue, pid, COLOR["body"], W, H, font_label, font_note)

        # 手脚
        parts = [
            (p.get("hand_l"), "Shoot Hand", COLOR["hand_l"]),
            (p.get("hand_r"), "Guide Hand", COLOR["hand_r"]),
            (p.get("foot_l"), "Lead Foot",  COLOR["foot_l"]),
            (p.get("foot_r"), "Back Foot",  COLOR["foot_r"]),
        ]
        for part_data, part_label, part_color in parts:
            if part_data:
                draw_part(draw, part_data, part_label, part_color, W, H, font_label, font_note)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(out_path, "JPEG", quality=90)


# ── Markdown 报告 ─────────────────────────────────────────────────────────────

ISSUE_TYPE_CN = {
    "flat_trajectory":       "出手弧度过平",
    "elbow_flare":           "肘部外翻",
    "no_wrist_follow":       "手腕未随挥",
    "late_release":          "出手点过低",
    "off_balance_shot":      "出手不稳",
    "no_leg_bend":           "膝盖未弯曲蓄力",
    "ball_watching":         "持球低头",
    "poor_ball_handle":      "控球不稳",
    "over_dribble":          "过度运球",
    "no_weak_hand":          "弱手保护不足",
    "poor_footwork":         "步法不到位",
    "wrong_pivot":           "转身步法错误",
    "late_closeout":         "补防关闭过晚",
    "poor_def_stance":       "防守站位差",
    "no_box_out":            "未卡位抢篮板",
    "ball_denial_miss":      "未做到断球位防守",
    "poor_drive_angle":      "突破角度差",
    "late_shot_fake":        "未用假动作",
    "good_form":             "技术正确",
    "good_movement":         "移动优秀",
    "good_defense":          "防守积极",
}

PART_CN = {
    "body":   "身体重心",
    "hand_l": "投篮手",
    "hand_r": "辅助手",
    "foot_l": "前脚",
    "foot_r": "后脚",
}


def generate_report(data: dict, annotated_frames: dict[str, Path]) -> str:
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    score = data.get("overall_score", "N/A")

    lines += [
        "# 篮球 教练分析报告",
        "",
        f"> 分析时间：{ts}　｜　综合评分：**{score} / 10**",
        "",
    ]

    # 帧标注
    lines += ["## 关键帧标注", ""]
    frame_data = data.get("frames", {})
    for fn in sorted(annotated_frames.keys(), key=lambda x: int(x)):
        img_path = annotated_frames[fn]
        finfo = frame_data.get(fn, {})
        summary = finfo.get("frame_summary", "")
        lines += [f"### Frame {fn}", "", f"![Frame {fn}](basketball_annotated/{img_path.name})", ""]
        if summary:
            lines += [f"> {summary}", ""]

        # 本帧问题汇总
        issues = []
        for p in finfo.get("players", []):
            pid = p.get("id", "P1")
            body_issue = p.get("body_issue_type", "")
            body_note  = p.get("body_issue_note", "")
            if body_issue and body_issue not in ("good_form", "good_movement"):
                issues.append(f"**{pid} 身体** — {ISSUE_TYPE_CN.get(body_issue, body_issue)}：{body_note}")
            for part_key, part_cn in PART_CN.items():
                if part_key == "body":
                    continue
                pd = p.get(part_key, {})
                if pd:
                    it = pd.get("issue_type", "")
                    note = pd.get("issue_note", "")
                    if it and it not in ("good_form", "good_movement"):
                        issues.append(f"**{pid} {part_cn}** — {ISSUE_TYPE_CN.get(it, it)}：{note}")
        if issues:
            lines += ["**本帧问题：**", ""]
            for iss in issues:
                lines.append(f"- {iss}")
            lines += [""]

    # 逐人详细分析
    lines += ["---", "", "## 球员个人分析", ""]
    for pid, pa in sorted(data.get("player_analysis", {}).items()):
        rating    = pa.get("overall_rating", "N/A")
        strengths = pa.get("strengths", [])
        issues    = pa.get("issues", [])
        improve   = pa.get("improvement", "")

        lines += [f"### {pid}　评分：{rating} / 10", ""]
        if strengths:
            lines += ["**✅ 亮点**", ""]
            for s in strengths:
                lines.append(f"- {s}")
            lines += [""]
        if issues:
            lines += ["**❌ 问题记录**", "", "| 帧 | 问题类型 | 部位 | 描述 |", "|---|---|---|---|"]
            for iss in issues:
                fn   = iss.get("frame", "?")
                it   = ISSUE_TYPE_CN.get(iss.get("type", ""), iss.get("type", ""))
                part = PART_CN.get(iss.get("body_part", "body"), iss.get("body_part", ""))
                det  = iss.get("detail", "")
                lines.append(f"| Frame {fn} | {it} | {part} | {det} |")
            lines += [""]
        if improve:
            lines += ["**🎯 训练建议**", "", improve, ""]
        lines += ["---", ""]

    # 总结
    session_sum = data.get("session_summary", "")
    if session_sum:
        lines += ["## 训练总结", "", session_sum, ""]

    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    frame_files = sorted(FRAMES_DIR.glob("frame_*.jpg"))
    if not frame_files:
        print("Error: output/frames/ 下没有帧文件，请先运行 coach.py 提取帧")
        return

    print(f"共找到 {len(frame_files)} 帧，开始篮球技术分析...")
    data = call_gpt4o(frame_files)
    print("  → GPT-4o 分析完成")

    annotated_map: dict[str, Path] = {}
    print("生成标注图片...")
    for i, frame_path in enumerate(frame_files, 1):
        fn_key  = str(i)
        finfo   = data.get("frames", {}).get(fn_key, {})
        players = finfo.get("players", [])
        out_path = ANNOTATED_DIR / frame_path.name
        annotate_frame(frame_path, players, out_path)
        annotated_map[fn_key] = out_path
        print(f"  → Frame {i:02d} 标注完成")

    print("生成 Markdown 报告...")
    report_md = generate_report(data, annotated_map)
    REPORT_PATH.write_text(report_md, encoding="utf-8")

    print(f"\n✅ 完成！")
    print(f"   标注图片：{ANNOTATED_DIR}/")
    print(f"   分析报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()
