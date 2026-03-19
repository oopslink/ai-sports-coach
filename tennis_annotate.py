#!/usr/bin/env python3
"""
tennis_annotate.py — 网球教练标注工具
1. 把所有帧一次性发给 GPT-4o，返回球员身体部位坐标 + 技术问题
2. 用 PIL 在每帧上标注：身体圆圈、手脚点位、问题区域（英文标签）
3. 生成含标注图片的逐帧分析 Markdown 报告
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
FRAMES_DIR    = Path("output/tennis/frames")
ANNOTATED_DIR = Path("output/tennis/annotated")
REPORT_PATH   = Path(f"output/tennis/annotate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

# ── 颜色（PIL RGB）────────────────────────────────────────────────────────────
COLOR = {
    "body":         ( 30, 144, 255),   # 蓝 — 身体重心
    "hand_l":       ( 50, 200,  80),   # 绿 — 持拍手
    "hand_r":       ( 20, 160,  50),   # 深绿 — 非持拍手
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
    # 技术问题 — 挥拍与接触
    "late_backswing":        "LATE BACKSWING",
    "wrong_grip":            "WRONG GRIP",
    "grip_change_error":     "GRIP CHANGE ERR",
    "wrong_contact_point":   "WRONG CONTACT",
    "elbow_drop":            "ELBOW DROP",
    "no_hip_rotation":       "NO HIP ROT",
    "shoulder_rot_late":     "LATE SHOULDER",
    "poor_follow_through":   "NO FOLLOW-THRU",
    # 步法与位置
    "poor_footwork":         "POOR FOOTWORK",
    "no_split_step":         "NO SPLIT STEP",
    "late_weight_transfer":  "LATE WEIGHT",
    "wrong_stance":          "WRONG STANCE",
    "wrong_court_position":  "WRONG POSITION",
    # 发球专项
    "poor_serve_toss":       "BAD TOSS",
    "no_leg_drive":          "NO LEG DRIVE",
    # 整体
    "off_balance":           "OFF BALANCE",
    "telegraphing":          "TELEGRAPH",
    "wrong_spin":            "WRONG SPIN",
    # 正面
    "good_form":             "GOOD FORM",
    "good_footwork":         "GOOD FOOTWORK",
    "good_tactics":          "GOOD TACTICS",
}

# ── GPT-4o System Prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a professional tennis coach analyzing training footage for technique improvement.
You will receive sequential video frames from the same tennis session.

Your task is sports biomechanics analysis — describe player body part POSITIONS using spatial coordinates only.
Do NOT attempt to identify the person. Focus on posture, stroke mechanics, and movement quality.

CRITICAL — COORDINATE ACCURACY:
Before estimating any coordinates, carefully scan the entire frame to find where the player actually is.
The player may be anywhere in the frame — left side, right side, center, near or far.
Do NOT default to center (0.5, 0.5). Look at the actual pixel position of each body part.
For example, if the player stands on the left third of the image, x_pct values should be around 0.1–0.35.
Estimate each body part's pixel center, then divide by image width/height to get x_pct / y_pct.

For each frame, locate the player and their limbs:
- body: center of mass / torso center (mid-chest area)
- hand_l: racket hand (dominant hand holding racket)
- hand_r: off hand (non-dominant hand)
- foot_l: front/lead foot (ankle/shoe center)
- foot_r: back foot (ankle/shoe center)

All positions as fractions of image width (x_pct) and height (y_pct), range 0.0-1.0.
Radius (radius_pct) relative to image width: body ~0.06, limbs ~0.03.

Classify technique issues using ONLY these types:
- late_backswing: racket not prepared / backswing starts too late
- wrong_grip: incorrect grip type for the shot (Eastern/Western/Continental)
- grip_change_error: failed to change grip between forehand and backhand
- wrong_contact_point: contact point too far back, too close or too late in swing arc
- elbow_drop: elbow drops on serve or overhead
- no_hip_rotation: insufficient hip and torso rotation reducing power
- shoulder_rot_late: shoulder rotation delayed, arm leads without trunk support
- poor_follow_through: incomplete follow-through after contact
- poor_footwork: feet not positioned correctly, wrong court position
- no_split_step: not performing split step before opponent contacts ball
- late_weight_transfer: body weight still on back foot through contact
- wrong_stance: wrong stance (open/closed/neutral) for shot type
- wrong_court_position: positioned too close/far from baseline, wrong zone
- poor_serve_toss: ball toss inconsistent, wrong position (forward/behind)
- no_leg_drive: insufficient leg push on serve or overhead
- off_balance: loss of balance during or after shot
- telegraphing: shot direction visible to opponent before contact
- wrong_spin: using topspin/slice/flat in wrong tactical situation
- good_form: correct technique — highlight positively
- good_footwork: good court movement and positioning — highlight positively
- good_tactics: smart shot selection or tactical movement — highlight positively

ARROWS — For each frame also provide 1-4 arrows that explain movement paths or posture corrections.
Arrow types and when to use them:
- swing_path:      Orange curved arrow — actual racket/arm swing trajectory observed
- correction:      Green dashed arrow  — where a body part SHOULD move (correct direction)
- rotation:        Yellow arc arrow    — hip or shoulder rotation direction
- kinetic_chain:   Cyan arrow          — energy transfer sequence (e.g. foot → knee → hip → arm)
- weight_transfer: Purple arrow        — body weight shift direction
- movement:        White arrow         — player footwork / court movement direction

Each arrow has a start point (from_x/from_y), an optional bezier control point (ctrl_x/ctrl_y) for curves,
an end point (to_x/to_y), and a short English label (≤4 words).
All coordinate values are fractions of image width/height (0.0–1.0), same rule as body parts.
Provide arrows ONLY where they add clear coaching value. Omit the field entirely for frames with no useful arrows.

issue_note and frame_summary MUST be in ENGLISH.
Player analysis fields (strengths, issues detail, improvement) should be in Chinese.

Respond ONLY with valid JSON (no markdown):
{
  "frames": {
    "1": {
      "players": [
        {
          "id": "P1",
          "body":   {"x_pct": 0.50, "y_pct": 0.50, "radius_pct": 0.06},
          "hand_l": {"x_pct": 0.55, "y_pct": 0.45, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "hand_r": {"x_pct": 0.45, "y_pct": 0.50, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "foot_l": {"x_pct": 0.48, "y_pct": 0.70, "radius_pct": 0.03, "issue_type": "poor_footwork", "issue_note": "Lead foot too far back"},
          "foot_r": {"x_pct": 0.55, "y_pct": 0.72, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "body_issue_type": "no_hip_rotation",
          "body_issue_note": "Hips facing forward, no rotation through contact"
        }
      ],
      "arrows": [
        {"type": "swing_path",      "from_x": 0.52, "from_y": 0.45, "ctrl_x": 0.56, "ctrl_y": 0.38, "to_x": 0.60, "to_y": 0.32, "label": "racket path"},
        {"type": "correction",      "from_x": 0.50, "from_y": 0.55, "to_x": 0.53, "to_y": 0.50, "label": "hip rotate"},
        {"type": "weight_transfer", "from_x": 0.48, "from_y": 0.65, "to_x": 0.51, "to_y": 0.63, "label": "shift forward"}
      ],
      "frame_summary": "Forehand shot, late backswing, hips not rotating."
    }
  },
  "player_analysis": {
    "P1": {
      "overall_rating": 6,
      "strengths": ["优点1（中文）", "优点2"],
      "issues": [
        {"frame": 3, "type": "late_backswing", "body_part": "body", "detail": "中文详细描述"}
      ],
      "improvement": "可操作训练建议（中文，分3条列出）"
    }
  },
  "session_summary": "本次训练整体技术评价（中文，3-5句）",
  "overall_score": 6
}"""


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise RuntimeError(f"JSON 解析失败:\n{raw}")


# 单帧分析 prompt（精简版，只要坐标+箭头）
FRAME_SYSTEM_PROMPT = """You are a professional tennis coach analyzing youth tennis training footage for technique improvement.
This is an official sports coaching session. Analyze body posture, racket mechanics, and footwork only.

CRITICAL — find where the player actually stands before estimating any coordinate.
The player may be anywhere (left/right/center). Scan the full image first.
x_pct = pixel_x / image_width,  y_pct = pixel_y / image_height  (range 0.0–1.0)
body radius_pct ~0.06,  limbs radius_pct ~0.03  (relative to image width)

Issue types (use exact keys):
late_backswing | wrong_grip | grip_change_error | wrong_contact_point | elbow_drop |
no_hip_rotation | shoulder_rot_late | poor_follow_through | poor_footwork |
no_split_step | late_weight_transfer | wrong_stance | wrong_court_position |
poor_serve_toss | no_leg_drive | off_balance | telegraphing | wrong_spin |
good_form | good_footwork | good_tactics

Arrow types: swing_path (orange) | correction (green dashed) | rotation (yellow) |
kinetic_chain (cyan) | weight_transfer (purple) | movement (white)
Provide 1–3 arrows showing actual movement paths or correction directions.
Arrow coords must be near the player's actual position in the image.

Respond ONLY with valid JSON (no markdown):
{
  "players": [{"id":"P1",
    "body":   {"x_pct":0.0,"y_pct":0.0,"radius_pct":0.06},
    "hand_l": {"x_pct":0.0,"y_pct":0.0,"radius_pct":0.03,"issue_type":"","issue_note":""},
    "hand_r": {"x_pct":0.0,"y_pct":0.0,"radius_pct":0.03,"issue_type":"","issue_note":""},
    "foot_l": {"x_pct":0.0,"y_pct":0.0,"radius_pct":0.03,"issue_type":"","issue_note":""},
    "foot_r": {"x_pct":0.0,"y_pct":0.0,"radius_pct":0.03,"issue_type":"","issue_note":""},
    "body_issue_type":"","body_issue_note":""}],
  "arrows": [
    {"type":"swing_path","from_x":0.0,"from_y":0.0,"ctrl_x":0.0,"ctrl_y":0.0,"to_x":0.0,"to_y":0.0,"label":"racket path"},
    {"type":"correction","from_x":0.0,"from_y":0.0,"to_x":0.0,"to_y":0.0,"label":"finish high"}
  ],
  "frame_summary": "one sentence in English"
}"""


def _analyze_single_frame(client, frame_path: Path, frame_num: int) -> dict:
    """单帧请求：精确定位 + 箭头。"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": FRAME_SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text",
                 "text": f"Tennis training footage frame {frame_num}. Perform biomechanics analysis: locate body parts as spatial coordinates, identify technique issues, and add coaching arrows. Return JSON only."},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{encode_image(frame_path)}", "detail": "high"}},
            ]},
        ],
        max_tokens=1200,
    )
    return _parse_json(response.choices[0].message.content)


def _analyze_summary(client, frame_results: dict) -> dict:
    """根据各帧结果，做一次文字汇总：player_analysis + session_summary。"""
    issues_text = []
    for fn, fdata in sorted(frame_results.items(), key=lambda x: int(x[0])):
        for p in fdata.get("players", []):
            pid = p.get("id", "P1")
            for part in ["body", "hand_l", "hand_r", "foot_l", "foot_r"]:
                if part == "body":
                    it = p.get("body_issue_type", "")
                    note = p.get("body_issue_note", "")
                else:
                    pd = p.get(part, {})
                    it = pd.get("issue_type", "") if pd else ""
                    note = pd.get("issue_note", "") if pd else ""
                if it and it not in ("good_form", "good_footwork", "good_tactics", ""):
                    issues_text.append(f"Frame {fn} {pid} {part}: {it} — {note}")
        summary = fdata.get("frame_summary", "")
        if summary:
            issues_text.append(f"Frame {fn} summary: {summary}")

    prompt = (
        "Based on this tennis session analysis, provide player_analysis and session_summary in JSON.\n"
        "Issues found:\n" + "\n".join(issues_text) +
        '\n\nRespond ONLY with valid JSON:\n'
        '{"player_analysis":{"P1":{"overall_rating":7,"strengths":["中文优点1","优点2"],'
        '"issues":[{"frame":3,"type":"late_backswing","body_part":"hand_l","detail":"中文描述"}],'
        '"improvement":"中文建议，分3条"}},'
        '"session_summary":"中文总结3-5句","overall_score":7}'
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    return _parse_json(response.choices[0].message.content)


def call_gpt4o(frames: list[Path]) -> dict:
    """逐帧独立请求（精确坐标+箭头），最后一次汇总分析。"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)
    frame_results: dict[str, dict] = {}

    for i, frame_path in enumerate(frames, 1):
        print(f"  → 分析 Frame {i:02d} ...")
        try:
            fdata = _analyze_single_frame(client, frame_path, i)
        except Exception as e:
            print(f"     ⚠ Frame {i} 分析失败，跳过: {e}")
            fdata = {}
        frame_results[str(i)] = fdata

    print("  → 汇总分析中...")
    try:
        summary = _analyze_summary(client, frame_results)
    except Exception as e:
        print(f"  ⚠ 汇总失败: {e}")
        summary = {"player_analysis": {}, "session_summary": "", "overall_score": 7}

    return {
        "frames": frame_results,
        "player_analysis": summary.get("player_analysis", {}),
        "session_summary":  summary.get("session_summary", ""),
        "overall_score":    summary.get("overall_score", 7),
    }


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


import math

# ── 箭头配色 ──────────────────────────────────────────────────────────────────
ARROW_STYLES = {
    "swing_path":      {"color": (255, 140,   0), "width": 5, "dash": False},  # 橙
    "correction":      {"color": ( 50, 220,  80), "width": 4, "dash": True },  # 绿虚线
    "rotation":        {"color": (255, 220,  40), "width": 4, "dash": False},  # 黄
    "kinetic_chain":   {"color": ( 40, 210, 210), "width": 4, "dash": False},  # 青
    "weight_transfer": {"color": (180,  80, 220), "width": 4, "dash": False},  # 紫
    "movement":        {"color": (230, 230, 230), "width": 4, "dash": False},  # 白
}
SHADOW_COLOR = (0, 0, 0, 160)


def _bezier_pts(x0, y0, cx, cy, x1, y1, steps=32):
    return [
        ((1-t)**2 * x0 + 2*(1-t)*t * cx + t**2 * x1,
         (1-t)**2 * y0 + 2*(1-t)*t * cy + t**2 * y1)
        for t in (i / steps for i in range(steps + 1))
    ]


def _arrowhead(x0, y0, x1, y1, size=20):
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length == 0:
        return None
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    return [(x1, y1),
            (x1 - ux*size + px*size*0.42, y1 - uy*size + py*size*0.42),
            (x1 - ux*size - px*size*0.42, y1 - uy*size - py*size*0.42)]


def _draw_polyline_shadow(draw, pts, width):
    """先画黑色描边，再画彩色线（双层描边效果）。"""
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=SHADOW_COLOR, width=width + 3)


def _draw_polyline(draw, pts, color_a, width, dashed=False):
    if dashed:
        # 每隔一段画一段
        seg = max(2, len(pts) // 8)
        for i in range(0, len(pts) - 1, seg * 2):
            end = min(i + seg, len(pts) - 1)
            draw.line([pts[i], pts[end]], fill=color_a, width=width)
    else:
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=color_a, width=width)


def draw_arrow(draw, arrow_data, img_w, img_h, font_label):
    """绘制带描边的粗箭头，支持直线/Bezier曲线。"""
    atype  = arrow_data.get("type", "swing_path")
    style  = ARROW_STYLES.get(atype, ARROW_STYLES["swing_path"])
    color  = style["color"]
    width  = style["width"]
    dashed = style["dash"]
    label  = arrow_data.get("label", "")

    fx = float(arrow_data.get("from_x", 0)) * img_w
    fy = float(arrow_data.get("from_y", 0)) * img_h
    tx = float(arrow_data.get("to_x",   0)) * img_w
    ty = float(arrow_data.get("to_y",   0)) * img_h

    cx_raw = arrow_data.get("ctrl_x")
    cy_raw = arrow_data.get("ctrl_y")
    if cx_raw is not None and cy_raw is not None:
        pts = _bezier_pts(fx, fy, float(cx_raw)*img_w, float(cy_raw)*img_h, tx, ty)
    else:
        pts = [(fx, fy), (tx, ty)]

    color_a = color + (230,)

    # 先黑色描边层
    _draw_polyline_shadow(draw, pts, width)
    # 再彩色线
    _draw_polyline(draw, pts, color_a, width, dashed)

    # 箭头头部：先黑色底，再彩色
    ref = pts[max(0, len(pts) - 5)]
    head = _arrowhead(ref[0], ref[1], tx, ty, size=20)
    if head:
        draw.polygon(head, fill=SHADOW_COLOR)
        draw.polygon(head, fill=color_a)

    # 标签：沿箭头方向放置，带描边
    if label:
        mid = pts[len(pts) // 2]
        mx, my = int(mid[0]) + 6, int(mid[1]) - 22
        font = get_font(14)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        pad = 4
        # 半透明彩色背景
        draw.rectangle([mx - pad, my - pad, mx + tw + pad, my + th + pad],
                       fill=color + (200,))
        # 白色文字
        draw.text((mx, my), label, font=font, fill=(255, 255, 255, 245))


# ── 身体部位标注（仅标注有问题的部位，引导线拉到侧边）────────────────────────

def _label_box(draw, lx, ly, text, sub_text, color, font_main, font_sub, align_right=False):
    """在 (lx, ly) 绘制标签框（彩色背景 + 白色主文 + 黄色副文）。"""
    pad = 5
    b1 = draw.textbbox((0, 0), text, font=font_main)
    tw1, th1 = b1[2]-b1[0], b1[3]-b1[1]
    b2 = draw.textbbox((0, 0), sub_text, font=font_sub) if sub_text else (0, 0, 0, 0)
    tw2, th2 = (b2[2]-b2[0], b2[3]-b2[1]) if sub_text else (0, 0)

    box_w = max(tw1, tw2) + pad * 2
    box_h = th1 + (th2 + 3 if sub_text else 0) + pad * 2

    if align_right:
        lx = lx - box_w

    # 黑色描边框
    draw.rectangle([lx-1, ly-1, lx+box_w+1, ly+box_h+1], fill=(0, 0, 0, 180))
    # 彩色背景框
    draw.rectangle([lx, ly, lx+box_w, ly+box_h], fill=color + (210,))
    # 左侧竖条强调色
    draw.rectangle([lx, ly, lx+4, ly+box_h], fill=(255, 255, 255, 180))

    draw.text((lx + pad + 2, ly + pad), text, font=font_main, fill=(255, 255, 255, 245))
    if sub_text:
        draw.text((lx + pad + 2, ly + pad + th1 + 3), sub_text, font=font_sub,
                  fill=(255, 230, 60, 230))
    return box_w, box_h


def annotate_frame(frame_path: Path, frame_info: dict, out_path: Path):
    img = Image.open(frame_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    W, H = img.size

    font_main = get_font(15)
    font_sub  = get_font(12)

    players = frame_info.get("players", [])
    arrows  = frame_info.get("arrows", [])

    # ── Step 1: 收集所有「有问题」的部位 ────────────────────────────────────
    issue_entries = []   # (cx, cy, dot_color, label_text, tag, note)
    player_x_sum = 0
    player_count = 0

    for p in players:
        body = p.get("body", {})
        bx = int(float(body.get("x_pct", 0.3)) * W)
        by = int(float(body.get("y_pct", 0.4)) * H)
        player_x_sum += bx
        player_count += 1

        # body issue
        b_it   = p.get("body_issue_type", "")
        b_note = p.get("body_issue_note", "")
        if b_it and b_it not in ("good_form", "good_footwork", "good_tactics"):
            tag = ISSUE_LABELS.get(b_it, b_it.upper())
            issue_entries.append((bx, by, COLOR["body"], "Body", tag, b_note))

        for pkey, pcol, pname in [
            ("hand_l", COLOR["hand_l"], "Racket Hand"),
            ("hand_r", COLOR["hand_r"], "Off Hand"),
            ("foot_l", COLOR["foot_l"], "Lead Foot"),
            ("foot_r", COLOR["foot_r"], "Back Foot"),
        ]:
            pd = p.get(pkey) or {}
            it   = pd.get("issue_type", "")
            note = pd.get("issue_note", "")
            if not it or it in ("good_form", "good_footwork", "good_tactics"):
                continue
            px = int(float(pd.get("x_pct", 0)) * W)
            py = int(float(pd.get("y_pct", 0)) * H)
            tag = ISSUE_LABELS.get(it, it.upper())
            issue_entries.append((px, py, pcol, pname, tag, note))

    # ── Step 2: 判断标签放置方向（球员在左→标签放右，球员在右→标签放左）────
    avg_x = (player_x_sum / player_count) if player_count else W * 0.3
    place_right = avg_x < W * 0.55
    label_x = int(avg_x + W * 0.22) if place_right else int(avg_x - W * 0.22)
    label_x = max(10, min(label_x, W - 220))

    # ── Step 3: 画箭头（最先画，在最底层）──────────────────────────────────
    for arrow in arrows:
        try:
            draw_arrow(draw, arrow, W, H, font_main)
        except Exception:
            pass

    # ── Step 4: 对每个问题部位画小圆点 + 引导线 + 侧边标签 ─────────────────
    label_y = max(30, int(H * 0.08))
    label_gap = 10

    for (cx, cy, dot_col, pname, tag, note) in issue_entries:
        is_good = tag in ("GOOD FORM", "GOOD FOOTWORK", "GOOD TACTICS")
        ring_col = COLOR["good_ring"] if is_good else COLOR["issue_ring"]

        # 小圆点（body part 位置）
        r = 10
        draw.ellipse([cx-r-2, cy-r-2, cx+r+2, cy+r+2], outline=(0,0,0,180), width=3)
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=ring_col+(230,), width=3)
        draw.ellipse([cx-4, cy-4, cx+4, cy+4], fill=dot_col+(240,))

        # 引导线目标点
        anchor_x = label_x if place_right else label_x + 200
        anchor_y = label_y + 16

        # 折线引导：body part → 中间折点 → 标签锚点
        mid_x = (cx + anchor_x) // 2
        draw.line([(cx, cy), (mid_x, cy)],       fill=(0,0,0,120),     width=3)
        draw.line([(cx, cy), (mid_x, cy)],       fill=dot_col+(180,),  width=2)
        draw.line([(mid_x, cy), (anchor_x, anchor_y)], fill=(0,0,0,120),     width=3)
        draw.line([(mid_x, cy), (anchor_x, anchor_y)], fill=dot_col+(180,),  width=2)

        # 标签框
        short_note = textwrap.shorten(note, width=28, placeholder="…") if note else ""
        bw, bh = _label_box(
            draw, label_x, label_y,
            f"{pname}: {tag}", short_note,
            dot_col, font_main, font_sub,
            align_right=not place_right,
        )
        label_y += bh + label_gap

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(out_path, "JPEG", quality=90)


# ── Markdown 报告 ─────────────────────────────────────────────────────────────

ISSUE_TYPE_CN = {
    "late_backswing":        "引拍过晚",
    "wrong_grip":            "握拍错误",
    "grip_change_error":     "换拍未完成",
    "wrong_contact_point":   "击球点错误",
    "elbow_drop":            "肘部下垂",
    "no_hip_rotation":       "髋肩未转动",
    "shoulder_rot_late":     "肩部转动过晚",
    "poor_follow_through":   "随挥不足",
    "poor_footwork":         "步法不到位",
    "no_split_step":         "缺少分步预判",
    "late_weight_transfer":  "重心转移过晚",
    "wrong_stance":          "站姿错误",
    "wrong_court_position":  "场位不合理",
    "poor_serve_toss":       "抛球不稳",
    "no_leg_drive":          "腿部蹬力不足",
    "off_balance":           "重心不稳",
    "telegraphing":          "动作路线暴露",
    "wrong_spin":            "旋转类型错误",
    "good_form":             "技术正确",
    "good_footwork":         "步法优秀",
    "good_tactics":          "战术意识好",
}

PART_CN = {
    "body":   "身体重心",
    "hand_l": "持拍手",
    "hand_r": "非持拍手",
    "foot_l": "前脚",
    "foot_r": "后脚",
}


def generate_report(data: dict, annotated_frames: dict[str, Path]) -> str:
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    score = data.get("overall_score", "N/A")

    lines += [
        "# 网球 教练分析报告",
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
        lines += [f"### Frame {fn}", "", f"![Frame {fn}](tennis_annotated/{img_path.name})", ""]
        if summary:
            lines += [f"> {summary}", ""]

        # 本帧问题汇总
        issues = []
        for p in finfo.get("players", []):
            pid = p.get("id", "P1")
            body_issue = p.get("body_issue_type", "")
            body_note  = p.get("body_issue_note", "")
            if body_issue and body_issue not in ("good_form", "good_footwork"):
                issues.append(f"**{pid} 身体** — {ISSUE_TYPE_CN.get(body_issue, body_issue)}：{body_note}")
            for part_key, part_cn in PART_CN.items():
                if part_key == "body":
                    continue
                pd = p.get(part_key, {})
                if pd:
                    it = pd.get("issue_type", "")
                    note = pd.get("issue_note", "")
                    if it and it not in ("good_form", "good_footwork"):
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

    # 训练总结
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

    print(f"共找到 {len(frame_files)} 帧，开始网球技术分析...")
    data = call_gpt4o(frame_files)
    print("  → GPT-4o 分析完成")

    annotated_map: dict[str, Path] = {}
    print("生成标注图片...")
    for i, frame_path in enumerate(frame_files, 1):
        fn_key   = str(i)
        finfo    = data.get("frames", {}).get(fn_key, {})
        out_path = ANNOTATED_DIR / frame_path.name
        annotate_frame(frame_path, finfo, out_path)
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
