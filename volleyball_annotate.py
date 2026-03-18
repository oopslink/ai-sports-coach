#!/usr/bin/env python3
"""
volleyball_annotate.py — 排球教练标注工具
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
FRAMES_DIR    = Path("output/volleyball/frames")
ANNOTATED_DIR = Path("output/volleyball/annotated")
REPORT_PATH   = Path(f"output/volleyball/annotate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

# ── 颜色（PIL RGB）────────────────────────────────────────────────────────────
COLOR = {
    "body":         ( 30, 144, 255),   # 蓝 — 身体重心
    "hand_l":       ( 50, 200,  80),   # 绿 — 左臂
    "hand_r":       ( 20, 160,  50),   # 深绿 — 右臂
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
    # 垫球（Dig）
    "improper_platform":     "WRONG PLATFORM",
    "poor_dig_angle":        "WRONG DIG ANG",
    "no_platform_lock":      "PLATFORM UNLOCK",
    # 传球（Set）
    "poor_set_hands":        "WRONG SET HANDS",
    "late_set_hands":        "LATE SET HANDS",
    "wrong_set_location":    "WRONG SET LOC",
    # 扣球（Spike）
    "poor_spike_approach":   "POOR APPROACH",
    "poor_arm_swing":        "POOR ARM SWING",
    "no_wrist_snap_spike":   "NO WRIST SNAP",
    "poor_jump_timing":      "BAD JUMP TIMING",
    # 发球（Serve）
    "bad_serve_toss":        "BAD TOSS",
    "poor_float_contact":    "BAD FLOAT HIT",
    # 拦网（Block）
    "poor_block_timing":     "BLOCK TIMING",
    "block_no_penetrate":    "NO PENETRATION",
    # 整体
    "poor_ready_pos":        "NOT READY",
    "off_balance":           "OFF BALANCE",
    "poor_serve_receive":    "POOR RECEPTION",
    "no_coverage":           "NO COVERAGE",
    # 正面
    "good_technique":        "GOOD TECH",
    "good_movement":         "GOOD MOVEMENT",
    "good_set":              "GOOD SET",
}

# ── GPT-4o System Prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a professional volleyball coach analyzing training footage for technique improvement.
You will receive sequential video frames from the same volleyball training session.

Your task is sports biomechanics analysis — describe player body part POSITIONS using spatial coordinates only.
Do NOT attempt to identify the person. Focus on hitting mechanics, setting, digging, and court movement.

For each frame, locate the player and their limbs:
- body: center of mass / torso center
- hand_l: left arm/hand position
- hand_r: right arm/hand position
- foot_l: front/lead foot
- foot_r: back foot

All positions as fractions of image width (x_pct) and height (y_pct), range 0.0-1.0.
Radius: body ~0.06, limbs ~0.03.

Classify technique issues using ONLY these types:
- improper_platform: platform angle wrong on dig (arms not flat, thumbs not parallel)
- poor_dig_angle: dig angle sends ball offline from target (setter position)
- no_platform_lock: elbows bent during platform contact, reducing consistency
- poor_set_hands: hands not forming correct diamond window for overhead set
- late_set_hands: hands not raised and ready before ball arrives for set
- wrong_set_location: set too tight to net, too far from net, or wrong height for attacker
- poor_spike_approach: wrong 3/4-step spike approach rhythm or approach angle
- poor_arm_swing: spike arm swing not using full shoulder rotation and extension
- no_wrist_snap_spike: no wrist snap/press on spike, losing downward angle
- poor_jump_timing: approach timing results in contact at falling phase not peak
- bad_serve_toss: ball toss inconsistent in position or height for serve type
- poor_float_contact: float serve contact off-center (ball will spin, losing float)
- poor_block_timing: jumping too early or too late for block attempt
- block_no_penetrate: block hands not penetrating over net to cut attack angle
- poor_ready_pos: not in ready athletic position between plays
- off_balance: loss of balance during or after contact
- poor_serve_receive: serve receive platform sends ball away from setter target zone
- no_coverage: teammates not in coverage positions after setter delivers set
- good_technique: correct technique — highlight positively
- good_movement: excellent court movement and positioning — highlight positively
- good_set: perfect set delivery for attacker — highlight positively

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
          "hand_l": {"x_pct": 0.43, "y_pct": 0.62, "radius_pct": 0.03, "issue_type": "improper_platform", "issue_note": "Left arm bent, platform not flat"},
          "hand_r": {"x_pct": 0.56, "y_pct": 0.60, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "foot_l": {"x_pct": 0.46, "y_pct": 0.74, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "foot_r": {"x_pct": 0.54, "y_pct": 0.74, "radius_pct": 0.03, "issue_type": "poor_ready_pos", "issue_note": "Feet too narrow for stable dig"},
          "body_issue_type": "off_balance",
          "body_issue_note": "Weight too far forward, can't recover after dig"
        }
      ],
      "frame_summary": "Dig attempt, platform uneven, off balance."
    }
  },
  "player_analysis": {
    "P1": {
      "overall_rating": 6,
      "strengths": ["优点1", "优点2"],
      "issues": [{"frame": 2, "type": "improper_platform", "body_part": "hand_l", "detail": "中文描述"}],
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
        {"type": "text", "text": f"Volleyball training footage — {len(frames)} sequential frames for biomechanics analysis:"}
    ]
    for i, frame in enumerate(frames, 1):
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encode_image(frame)}", "detail": "low"},
        })
        content.append({"type": "text", "text": f"[Frame {i}]"})

    print("  → 发送帧到 GPT-4o（排球技术分析）...")
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

    is_issue = issue_type and issue_type not in ("good_technique", "good_movement")
    is_good  = issue_type in ("good_technique", "good_movement")

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
            (p.get("hand_l"), "Left Arm",  COLOR["hand_l"]),
            (p.get("hand_r"), "Right Arm", COLOR["hand_r"]),
            (p.get("foot_l"), "Lead Foot", COLOR["foot_l"]),
            (p.get("foot_r"), "Back Foot", COLOR["foot_r"]),
        ]
        for part_data, part_label, part_color in parts:
            if part_data:
                draw_part(draw, part_data, part_label, part_color, W, H, font_label, font_note)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(out_path, "JPEG", quality=90)


# ── Markdown 报告 ─────────────────────────────────────────────────────────────

ISSUE_TYPE_CN = {
    "improper_platform":     "垫球平台错误",
    "poor_dig_angle":        "垫球角度偏差",
    "no_platform_lock":      "手臂未锁直",
    "poor_set_hands":        "传球手型错误",
    "late_set_hands":        "举手准备过晚",
    "wrong_set_location":    "传球落点错误",
    "poor_spike_approach":   "扣球助跑差",
    "poor_arm_swing":        "挥臂幅度不足",
    "no_wrist_snap_spike":   "扣球手腕未压",
    "poor_jump_timing":      "起跳时机错误",
    "bad_serve_toss":        "发球抛球差",
    "poor_float_contact":    "飘球接触点偏",
    "poor_block_timing":     "拦网时机差",
    "block_no_penetrate":    "拦网手未压网",
    "poor_ready_pos":        "准备姿势差",
    "off_balance":           "重心不稳",
    "poor_serve_receive":    "接发球到位率差",
    "no_coverage":           "未保护扣球",
    "good_technique":        "技术正确",
    "good_movement":         "移动优秀",
    "good_set":              "传球到位",
}

PART_CN = {
    "body":   "身体重心",
    "hand_l": "左臂",
    "hand_r": "右臂",
    "foot_l": "前脚",
    "foot_r": "后脚",
}


def generate_report(data: dict, annotated_frames: dict[str, Path]) -> str:
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    score = data.get("overall_score", "N/A")

    lines += [
        "# 排球 教练分析报告",
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
        lines += [f"### Frame {fn}", "", f"![Frame {fn}](volleyball_annotated/{img_path.name})", ""]
        if summary:
            lines += [f"> {summary}", ""]

        # 本帧问题汇总
        issues = []
        for p in finfo.get("players", []):
            pid = p.get("id", "P1")
            body_issue = p.get("body_issue_type", "")
            body_note  = p.get("body_issue_note", "")
            if body_issue and body_issue not in ("good_technique", "good_movement"):
                issues.append(f"**{pid} 身体** — {ISSUE_TYPE_CN.get(body_issue, body_issue)}：{body_note}")
            for part_key, part_cn in PART_CN.items():
                if part_key == "body":
                    continue
                pd = p.get(part_key, {})
                if pd:
                    it = pd.get("issue_type", "")
                    note = pd.get("issue_note", "")
                    if it and it not in ("good_technique", "good_movement"):
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

    print(f"共找到 {len(frame_files)} 帧，开始排球技术分析...")
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
