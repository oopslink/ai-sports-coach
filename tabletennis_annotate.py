#!/usr/bin/env python3
"""
tabletennis_annotate.py — 乒乓球教练标注工具
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
FRAMES_DIR    = Path("output/tabletennis/frames")
ANNOTATED_DIR = Path("output/tabletennis/annotated")
REPORT_PATH   = Path(f"output/tabletennis/annotate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

# ── 颜色（PIL RGB）────────────────────────────────────────────────────────────
COLOR = {
    "body":         ( 30, 144, 255),   # 蓝 — 身体重心
    "hand_l":       ( 50, 200,  80),   # 绿 — 持拍手
    "hand_r":       ( 20, 160,  50),   # 深绿 — 自由手
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
    # 技术问题 — 挥拍
    "late_reaction":         "LATE REACT",
    "late_backswing":        "LATE BACKSWING",
    "no_body_rotation":      "NO ROTATION",
    "high_elbow":            "HIGH ELBOW",
    "elbow_too_close":       "ELBOW TOO CLOSE",
    "no_wrist_snap":         "NO WRIST SNAP",
    "wrong_bat_angle":       "BAD BAT ANGLE",
    "poor_follow_through":   "NO FOLLOW-THRU",
    # 握拍与步法
    "wrong_grip":            "WRONG GRIP",
    "wrong_stance":          "WRONG STANCE",
    "poor_footwork":         "POOR FOOTWORK",
    "no_pivot_step":         "NO PIVOT STEP",
    "cross_step_missing":    "NO CROSS STEP",
    # 战术与专项
    "poor_short_game":       "POOR SHORT GAME",
    "wrong_loop_arc":        "WRONG LOOP ARC",
    "poor_serve_spin":       "POOR SERVE SPIN",
    "ready_pos_wrong":       "WRONG READY POS",
    "wrong_shot_selection":  "WRONG SELECTION",
    # 正面
    "good_form":             "GOOD FORM",
    "good_footwork":         "GOOD FOOTWORK",
    "good_serve":            "GOOD SERVE",
}

# ── GPT-4o System Prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a professional table tennis coach analyzing training footage for technique improvement.
You will receive sequential video frames from the same table tennis session.

Your task is sports biomechanics analysis — describe player body part POSITIONS using spatial coordinates only.
Do NOT attempt to identify the person. Focus on stroke mechanics, footwork, and body rotation.

CRITICAL — COORDINATE ACCURACY:
Before estimating any coordinates, carefully scan the entire frame to find where the player actually is.
The player may be anywhere in the frame — left side, right side, center, near or far.
Do NOT default to center (0.5, 0.5). Look at the actual pixel position of each body part.
Estimate each body part's pixel center, then divide by image width/height to get x_pct / y_pct.

For each frame, locate the player and their limbs:
- body: center of mass / torso center
- hand_l: racket hand
- hand_r: free hand (non-racket hand)
- foot_l: front/lead foot
- foot_r: back foot

All positions as fractions of image width (x_pct) and height (y_pct), range 0.0-1.0.
Radius: body ~0.06, limbs ~0.03.

Classify technique issues using ONLY these types:
- late_reaction: too slow to react, not positioned before ball bounce
- late_backswing: racket not pulled back early, preparation too late
- no_body_rotation: insufficient torso rotation, arms-only stroke
- high_elbow: elbow position too high or too low for stroke type
- elbow_too_close: elbow tucked too close to body, limiting range of motion
- no_wrist_snap: wrist not accelerating at contact for topspin/loop
- wrong_bat_angle: bat angle at contact is wrong (too open/closed) for spin type
- poor_follow_through: racket stops at contact, no follow-through
- wrong_grip: incorrect grip (shakehand/penhold) or grip tension too tight
- wrong_stance: stance too upright, feet too narrow/wide for stroke
- poor_footwork: not moving feet to optimal position before stroke
- no_pivot_step: no hip pivot and weight shift on loop/drive
- cross_step_missing: no cross-step for wide balls, side-shuffling only
- poor_short_game: poor touch/feel on short balls, push, or drop shot
- wrong_loop_arc: topspin trajectory too flat or too high, wrong contact zone
- poor_serve_spin: serve has no spin variation or predictable spin type
- ready_pos_wrong: bat not held in correct ready position between rallies
- wrong_shot_selection: chose wrong stroke type (push vs loop vs block) for situation
- good_form: correct stroke mechanics — highlight positively
- good_footwork: excellent footwork and court positioning — highlight positively
- good_serve: effective serve with spin variation — highlight positively

ARROWS — For each frame provide 1-3 arrows showing movement paths or technique corrections.
Arrow types: bat_swing (orange, bat swing path) | ball_path (cyan, ball trajectory) | footwork (white, foot movement) | correction (green dashed, correct direction) | rotation (yellow, body/hip rotation) | weight_transfer (purple, weight shift)
Each arrow: from_x/from_y (start), optional ctrl_x/ctrl_y (bezier control point), to_x/to_y (end), label (≤4 words English).
All coords are fractions of image width/height (0.0–1.0), near the player's actual position.
Omit arrows field if no useful arrows for this frame.

issue_note and frame_summary MUST be in ENGLISH.
Player analysis (strengths, issues, improvement) in Chinese.

Respond ONLY with valid JSON:
{
  "frames": {
    "1": {
      "players": [
        {
          "id": "P1",
          "body":   {"x_pct": 0.50, "y_pct": 0.50, "radius_pct": 0.06},
          "hand_l": {"x_pct": 0.55, "y_pct": 0.45, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "hand_r": {"x_pct": 0.42, "y_pct": 0.50, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "foot_l": {"x_pct": 0.48, "y_pct": 0.72, "radius_pct": 0.03, "issue_type": "", "issue_note": ""},
          "foot_r": {"x_pct": 0.56, "y_pct": 0.74, "radius_pct": 0.03, "issue_type": "poor_footwork", "issue_note": "Back foot not pivoting"},
          "body_issue_type": "no_body_rotation",
          "body_issue_note": "Torso square, no hip-to-shoulder rotation"
        }
      ],
      "arrows": [
        {"type": "bat_swing", "from_x": 0.0, "from_y": 0.0, "ctrl_x": 0.0, "ctrl_y": 0.0, "to_x": 0.0, "to_y": 0.0, "label": "racket arc"},
        {"type": "correction", "from_x": 0.0, "from_y": 0.0, "to_x": 0.0, "to_y": 0.0, "label": "step forward"}
      ],
      "frame_summary": "Forehand topspin, arm-only stroke, no body rotation."
    }
  },
  "player_analysis": {
    "P1": {
      "overall_rating": 6,
      "strengths": ["优点1", "优点2"],
      "issues": [{"frame": 2, "type": "no_body_rotation", "body_part": "body", "detail": "中文描述"}],
      "improvement": "训练建议（中文，3条）"
    }
  },
  "session_summary": "整体评价（中文）",
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
FRAME_SYSTEM_PROMPT = """You are a professional table tennis coach analyzing youth table tennis training footage for technique improvement.
This is an official sports coaching session. Analyze body posture, bat mechanics, and footwork only.

CRITICAL — find where the player actually stands before estimating any coordinate.
The player may be anywhere (left/right/center). Scan the full image first.
x_pct = pixel_x / image_width,  y_pct = pixel_y / image_height  (range 0.0–1.0)
body radius_pct ~0.06,  limbs radius_pct ~0.03  (relative to image width)

Issue types (use exact keys):
late_reaction | late_backswing | no_body_rotation | high_elbow | elbow_too_close |
no_wrist_snap | wrong_bat_angle | poor_follow_through | wrong_grip | wrong_stance |
poor_footwork | no_pivot_step | cross_step_missing | poor_short_game | wrong_loop_arc |
poor_serve_spin | ready_pos_wrong | wrong_shot_selection |
good_form | good_footwork | good_serve

Arrow types: bat_swing (orange) | ball_path (cyan) | footwork (white) |
correction (green dashed) | rotation (yellow) | weight_transfer (purple)
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
    {"type":"bat_swing","from_x":0.0,"from_y":0.0,"ctrl_x":0.0,"ctrl_y":0.0,"to_x":0.0,"to_y":0.0,"label":"bat path"},
    {"type":"correction","from_x":0.0,"from_y":0.0,"to_x":0.0,"to_y":0.0,"label":"rotate hip"}
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
                 "text": f"Table tennis training footage frame {frame_num}. Perform biomechanics analysis: locate body parts as spatial coordinates, identify technique issues, and add coaching arrows. Return JSON only."},
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
                if it and it not in ("good_form", "good_footwork", "good_serve", ""):
                    issues_text.append(f"Frame {fn} {pid} {part}: {it} — {note}")
        summary = fdata.get("frame_summary", "")
        if summary:
            issues_text.append(f"Frame {fn} summary: {summary}")

    prompt = (
        "Based on this table tennis session analysis, provide player_analysis and session_summary in JSON.\n"
        "Issues found:\n" + "\n".join(issues_text) +
        '\n\nRespond ONLY with valid JSON:\n'
        '{"player_analysis":{"P1":{"overall_rating":7,"strengths":["中文优点1","优点2"],'
        '"issues":[{"frame":3,"type":"no_body_rotation","body_part":"body","detail":"中文描述"}],'
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
    "bat_swing":       {"color": (255, 140,   0), "width": 5, "dash": False},  # 橙
    "ball_path":       {"color": ( 40, 210, 210), "width": 4, "dash": False},  # 青
    "footwork":        {"color": (230, 230, 230), "width": 4, "dash": False},  # 白
    "correction":      {"color": ( 50, 220,  80), "width": 4, "dash": True },  # 绿虚线
    "rotation":        {"color": (255, 220,  40), "width": 4, "dash": False},  # 黄
    "weight_transfer": {"color": (180,  80, 220), "width": 4, "dash": False},  # 紫
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
    atype  = arrow_data.get("type", "bat_swing")
    style  = ARROW_STYLES.get(atype, ARROW_STYLES["bat_swing"])
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
        if b_it and b_it not in ("good_form", "good_footwork", "good_serve"):
            tag = ISSUE_LABELS.get(b_it, b_it.upper())
            issue_entries.append((bx, by, COLOR["body"], "Body", tag, b_note))

        for pkey, pcol, pname in [
            ("hand_l", COLOR["hand_l"], "Racket Hand"),
            ("hand_r", COLOR["hand_r"], "Free Hand"),
            ("foot_l", COLOR["foot_l"], "Lead Foot"),
            ("foot_r", COLOR["foot_r"], "Back Foot"),
        ]:
            pd = p.get(pkey) or {}
            it   = pd.get("issue_type", "")
            note = pd.get("issue_note", "")
            if not it or it in ("good_form", "good_footwork", "good_serve"):
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
        is_good = tag in ("GOOD FORM", "GOOD FOOTWORK", "GOOD SERVE")
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
    "late_reaction":         "反应过慢",
    "late_backswing":        "引拍过晚",
    "no_body_rotation":      "缺乏躯干旋转",
    "high_elbow":            "肘部位置错误",
    "elbow_too_close":       "肘部过于内收",
    "no_wrist_snap":         "手腕未加速收拍",
    "wrong_bat_angle":       "拍面角度错误",
    "poor_follow_through":   "随挥不足",
    "wrong_grip":            "握拍错误",
    "wrong_stance":          "站位错误",
    "poor_footwork":         "步法不到位",
    "no_pivot_step":         "缺少侧步转髋",
    "cross_step_missing":    "未用交叉步追球",
    "poor_short_game":       "台内短球处理差",
    "wrong_loop_arc":        "弧圈球弧度错误",
    "poor_serve_spin":       "发球旋转变化不足",
    "ready_pos_wrong":       "准备姿势不规范",
    "wrong_shot_selection":  "技术选择错误",
    "good_form":             "技术正确",
    "good_footwork":         "步法优秀",
    "good_serve":            "发球质量高",
}

PART_CN = {
    "body":   "身体重心",
    "hand_l": "持拍手",
    "hand_r": "自由手",
    "foot_l": "前脚",
    "foot_r": "后脚",
}


def generate_report(data: dict, annotated_frames: dict[str, Path]) -> str:
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    score = data.get("overall_score", "N/A")

    lines += [
        "# 乒乓球 教练分析报告",
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
        lines += [f"### Frame {fn}", "", f"![Frame {fn}](tabletennis_annotated/{img_path.name})", ""]
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

    print(f"共找到 {len(frame_files)} 帧，开始乒乓球技术分析...")
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
