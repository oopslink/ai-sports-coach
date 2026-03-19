#!/usr/bin/env python3
"""
defense_annotate.py — 防守复盘标注工具
1. 把所有帧一次性发给 GPT-4o，要求跨帧一致编号球员并返回坐标 + 分析
2. 用 PIL 在每帧上画出球员圆圈、编号、问题标注
3. 生成含标注图片的详细防守报告（Markdown）
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

# ── 路径配置 ─────────────────────────────────────────────────────────────────
FRAMES_DIR   = Path("output/defense/frames")
ANNOTATED_DIR = Path("output/defense/annotated")
REPORT_PATH  = Path(f"output/defense/annotate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

# ── 颜色配置（PIL 用 RGB 元组）────────────────────────────────────────────────
COLOR = {
    "defender":      (220,  50,  50),   # 红 — 防守
    "offense":       ( 50, 120, 220),   # 蓝 — 进攻
    "issue_ring":    (255, 200,   0),   # 黄 — 问题高亮外圈
    "issue_text_bg": (255, 200,   0),
    "issue_text_fg": ( 30,  30,  30),
    "label_bg_def":  (180,  20,  20),
    "label_bg_off":  ( 20,  80, 180),
    "label_fg":      (255, 255, 255),
    "arrow":         (255, 180,   0),
}

# ── GPT-4o Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a professional flag football defensive coach analyzing training footage for technique improvement.
You will receive 12 sequential video frames (Frame 1-12) from the same play.

Your task is sports biomechanics and positional analysis — describe player POSITIONS and MOVEMENTS using spatial coordinates only.

CRITICAL — COORDINATE ACCURACY:
Before estimating any coordinates, carefully scan the entire frame to find where the player/climber actually is.
The subject may be anywhere in the frame — left side, right side, center, near or far.
Do NOT default to center (0.5, 0.5). Look at the actual pixel position of each body part.
Estimate each body part's pixel center, then divide by image width/height to get x_pct / y_pct.

For each frame, number players left-to-right by their horizontal position: defenders get D1, D2... (assign by leftmost→rightmost), offensive players get O1, O2...
Maintain consistent numbering within each frame based on spatial order.

For each visible player, estimate their center position as fractions of image width (x_pct) and height (y_pct), and radius as fraction of width (radius_pct ~0.04-0.07).

Classify any defensive technique issues using ONLY these types:
- missed_flag (failed to pull flag — late reach, wrong angle)
- false_step (incorrect first step direction — got faked)
- high_center (center of gravity too high — upright stance)
- lost_coverage (lost coverage gap — wrong zone)
- no_switch (failed switch — two defenders on same player)
- good_position (correct stance/positioning — highlight positively)

ARROWS — For each frame provide 1-3 arrows showing movement paths or tactical corrections.
Arrow types: coverage_path (orange, defender coverage route) | pursuit_angle (orange, pursuit direction to ball carrier) | reaction (yellow, reaction/movement direction) | correction (green dashed, correct defensive position) | zone_boundary (cyan, zone coverage boundary)
Each arrow: from_x/from_y (start), optional ctrl_x/ctrl_y (bezier control point), to_x/to_y (end), label (≤4 words English).
All coords are fractions of image width/height (0.0–1.0), near the player's actual position.
Omit arrows field if no useful arrows for this frame.

IMPORTANT: All "issue_note" and "frame_summary" values MUST be in ENGLISH.
Player analysis fields (strengths, issues detail, improvement) should be in Chinese.

Respond ONLY with valid JSON (no markdown, no extra text):
{
  "player_legend": {
    "D1": "defender: jersey color, screen position (e.g. left side defender, dark jersey)",
    "D2": "...",
    "O1": "offensive player description"
  },
  "frames": {
    "1": {
      "players": [
        {"id": "D1", "team": "defense", "x_pct": 0.35, "y_pct": 0.55, "radius_pct": 0.05, "issue_type": "high_center", "issue_note": "Too upright, lost lateral speed"},
        {"id": "O1", "team": "offense", "x_pct": 0.60, "y_pct": 0.50, "radius_pct": 0.05, "issue_type": "", "issue_note": ""}
      ],
      "arrows": [
        {"type": "coverage_path", "from_x": 0.35, "from_y": 0.55, "ctrl_x": 0.45, "ctrl_y": 0.50, "to_x": 0.55, "to_y": 0.48, "label": "coverage route"},
        {"type": "correction",    "from_x": 0.35, "from_y": 0.55, "to_x": 0.33, "to_y": 0.58, "label": "lower stance"}
      ],
      "frame_summary": "English summary of key defensive action in this frame (1-2 sentences)"
    }
  },
  "player_analysis": {
    "D1": {
      "position": "角卫/安全卫/线卫",
      "overall_rating": 6,
      "strengths": ["优点1（中文）", "优点2"],
      "issues": [
        {"frame": 6, "type": "missed_flag", "detail": "中文详细描述"}
      ],
      "improvement": "可操作训练建议（中文，分3条列出）"
    }
  },
  "team_summary": "团队防守整体评价（中文，3-5句）",
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
FRAME_SYSTEM_PROMPT = """You are a professional flag football defensive coach analyzing flag football defensive training footage for coaching session.
This is an official sports coaching session. Analyze player positions, defensive stances, and movement patterns only.

CRITICAL — find where each player actually stands before estimating any coordinate.
Players may be anywhere (left/right/center). Scan the full image first.
x_pct = pixel_x / image_width,  y_pct = pixel_y / image_height  (range 0.0–1.0)
radius_pct ~0.04–0.07  (relative to image width)

Number players left-to-right: defenders get D1, D2..., offensive players get O1, O2...

Issue types (use exact keys):
missed_flag | false_step | high_center | lost_coverage | no_switch | good_position

Arrow types: coverage_path (orange) | pursuit_angle (orange) | reaction (yellow) |
correction (green dashed) | zone_boundary (cyan dashed)
Provide 1–3 arrows showing actual movement paths or correction directions.
Arrow coords must be near the player's actual position in the image.

Respond ONLY with valid JSON (no markdown):
{
  "players": [
    {"id":"D1","team":"defense","x_pct":0.0,"y_pct":0.0,"radius_pct":0.05,"issue_type":"","issue_note":""},
    {"id":"O1","team":"offense","x_pct":0.0,"y_pct":0.0,"radius_pct":0.05,"issue_type":"","issue_note":""}
  ],
  "arrows": [
    {"type":"coverage_path","from_x":0.0,"from_y":0.0,"ctrl_x":0.0,"ctrl_y":0.0,"to_x":0.0,"to_y":0.0,"label":"coverage route"},
    {"type":"correction","from_x":0.0,"from_y":0.0,"to_x":0.0,"to_y":0.0,"label":"lower stance"}
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
                 "text": f"Flag football defensive training footage frame {frame_num}. Perform positional analysis: locate players as spatial coordinates, identify defensive issues, and add coaching arrows. Return JSON only."},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{encode_image(frame_path)}", "detail": "high"}},
            ]},
        ],
        max_tokens=1200,
    )
    return _parse_json(response.choices[0].message.content)


def _analyze_summary(client, frame_results: dict) -> dict:
    """根据各帧结果，做一次文字汇总：player_analysis + team_summary。"""
    issues_text = []
    for fn, fdata in sorted(frame_results.items(), key=lambda x: int(x[0])):
        for p in fdata.get("players", []):
            pid = p.get("id", "D1")
            it = p.get("issue_type", "")
            note = p.get("issue_note", "")
            if it and it not in ("good_position", ""):
                issues_text.append(f"Frame {fn} {pid}: {it} — {note}")
        summary = fdata.get("frame_summary", "")
        if summary:
            issues_text.append(f"Frame {fn} summary: {summary}")

    prompt = (
        "Based on this flag football defensive session analysis, provide player_analysis and team_summary in JSON.\n"
        "Issues found:\n" + "\n".join(issues_text) +
        '\n\nRespond ONLY with valid JSON:\n'
        '{"player_analysis":{"D1":{"position":"角卫","overall_rating":7,"strengths":["中文优点1","优点2"],'
        '"issues":[{"frame":3,"type":"high_center","detail":"中文描述"}],'
        '"improvement":"中文建议，分3条"}},'
        '"team_summary":"中文总结3-5句","overall_score":7}'
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
        summary = {"player_analysis": {}, "team_summary": "", "overall_score": 7}

    return {
        "frames": frame_results,
        "player_analysis": summary.get("player_analysis", {}),
        "team_summary":    summary.get("team_summary", ""),
        "overall_score":   summary.get("overall_score", 7),
    }


# ── 绘制标注 ──────────────────────────────────────────────────────────────────

def get_font(size: int, bold: bool = False):
    """Load system font, prefer bold variants for labels."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


import math

# ── 箭头配色 ──────────────────────────────────────────────────────────────────
ARROW_STYLES = {
    "coverage_path": {"color": (255, 140,   0), "width": 5, "dash": False},  # 橙
    "pursuit_angle": {"color": (255, 180,  40), "width": 4, "dash": False},  # 橙黄
    "reaction":      {"color": (255, 220,  40), "width": 4, "dash": False},  # 黄
    "correction":    {"color": ( 50, 220,  80), "width": 4, "dash": True },  # 绿虚线
    "zone_boundary": {"color": ( 40, 210, 210), "width": 3, "dash": True },  # 青虚线
}
SHADOW_COLOR = (0, 0, 0, 160)

ISSUE_ICONS = {
    "missed_flag":    "MISS FLAG",
    "false_step":     "FALSE STEP",
    "high_center":    "HIGH CENTER",
    "lost_coverage":  "LOST MAN",
    "no_switch":      "NO SWITCH",
    "good_position":  "GOOD POS",
}


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
    atype  = arrow_data.get("type", "coverage_path")
    style  = ARROW_STYLES.get(atype, ARROW_STYLES["coverage_path"])
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
    font_main = get_font(18)
    font_sub  = get_font(13)

    players = frame_info.get("players", [])
    arrows  = frame_info.get("arrows", [])

    # ── Step 1: 收集所有「有问题」的部位 ────────────────────────────────────
    issue_entries = []   # (cx, cy, dot_color, label_text, tag, note)
    player_x_sum = 0
    player_count = 0

    for p in players:
        pid   = p.get("id", "?")
        team  = p.get("team", "defense")
        x_pct = float(p.get("x_pct", 0.5))
        y_pct = float(p.get("y_pct", 0.5))
        r_pct = float(p.get("radius_pct", 0.05))
        issue_type = p.get("issue_type", "")
        issue_note = p.get("issue_note", "")

        cx = int(x_pct * W)
        cy = int(y_pct * H)
        r  = int(r_pct * W)
        r  = max(r, 24)   # 最小半径

        player_x_sum += cx
        player_count += 1

        is_issue  = issue_type and issue_type != "good_position"
        is_good   = issue_type == "good_position"
        ring_color = COLOR["defender"] if team == "defense" else COLOR["offense"]
        lbg = COLOR["label_bg_def"] if team == "defense" else COLOR["label_bg_off"]

        # 问题球员：外圈黄色警告圈
        if is_issue:
            draw.ellipse(
                [cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6],
                outline=COLOR["issue_ring"] + (220,), width=4
            )
        # 主圆圈
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=ring_color + (230,), width=3
        )
        # 球员编号标签（直接在圆圈旁绘制，保留多球员支持）
        icon = ISSUE_ICONS.get(issue_type, "")
        label_text = f"{pid}" + (f" {icon}" if icon else "")
        # draw inline label above circle
        font_lbl = get_font(18)
        bbox = draw.textbbox((0, 0), label_text, font=font_lbl)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 4
        lx0 = cx - tw // 2 - pad
        ly0 = cy - r - th - pad * 2 - 4
        lx1 = cx + tw // 2 + pad
        ly1 = cy - r - 4
        draw.rectangle([lx0, ly0, lx1, ly1], fill=lbg + (210,))
        draw.text((lx0 + pad, ly0 + pad), label_text, font=font_lbl, fill=COLOR["label_fg"])

        # 问题说明文字（侧边标签收集）
        if is_issue:
            issue_entries.append((cx, cy, ring_color, pid, ISSUE_ICONS.get(issue_type, issue_type.upper()), issue_note))

    # ── Step 2: 判断标签放置方向 ──────────────────────────────────────────
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

    # ── Step 4: 侧边问题标签 ─────────────────────────────────────────────
    label_y = max(30, int(H * 0.08))
    label_gap = 10

    for (cx, cy, dot_col, pname, tag, note) in issue_entries:
        anchor_x = label_x if place_right else label_x + 200
        anchor_y = label_y + 16

        mid_x = (cx + anchor_x) // 2
        draw.line([(cx, cy), (mid_x, cy)],       fill=(0,0,0,120),     width=3)
        draw.line([(cx, cy), (mid_x, cy)],       fill=dot_col+(180,),  width=2)
        draw.line([(mid_x, cy), (anchor_x, anchor_y)], fill=(0,0,0,120),     width=3)
        draw.line([(mid_x, cy), (anchor_x, anchor_y)], fill=dot_col+(180,),  width=2)

        short_note = textwrap.shorten(note, width=28, placeholder="…") if note else ""
        bw, bh = _label_box(
            draw, label_x, label_y,
            f"{pname}: {tag}", short_note,
            dot_col, font_main, font_sub,
            align_right=not place_right,
        )
        label_y += bh + label_gap

    # 合并到原图
    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(out_path, "JPEG", quality=90)


# ── 生成 Markdown 报告 ────────────────────────────────────────────────────────

ISSUE_TYPE_CN = {
    "missed_flag":   "拔旗失败",
    "false_step":    "反向启动",
    "high_center":   "重心过高",
    "lost_coverage": "漏人丢防",
    "no_switch":     "换防失败",
    "good_position": "站位优秀",
}


def generate_report(data: dict, annotated_frames: dict[str, Path]) -> str:
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    overall = data.get("overall_score", "N/A")

    lines += [
        f"# 腰旗橄榄球 防守复盘报告",
        f"",
        f"> 分析时间：{ts}　｜　综合防守评分：**{overall} / 10**",
        f"",
    ]

    # ── 球员图例 ──────────────────────────────────────────────────────────────
    legend = data.get("player_legend", {})
    if legend:
        lines += ["## 球员编号图例", "", "| 编号 | 描述 |", "|------|------|"]
        for pid, desc in legend.items():
            team_tag = "🔴 防" if pid.startswith("D") else "🔵 攻"
            lines.append(f"| **{pid}** {team_tag} | {desc} |")
        lines += [""]

    # ── 关键帧（标注版）──────────────────────────────────────────────────────
    lines += ["## 关键帧标注", ""]
    frame_data = data.get("frames", {})
    for fn in sorted(annotated_frames.keys(), key=lambda x: int(x)):
        img_path = annotated_frames[fn]
        finfo = frame_data.get(fn, {})
        summary = finfo.get("frame_summary", "")
        lines += [
            f"### Frame {fn}",
            f"",
            f"![Frame {fn} 标注](annotated/{img_path.name})",
            f"",
        ]
        if summary:
            lines += [f"> {summary}", ""]

        # 该帧球员问题列表
        players_in_frame = finfo.get("players", [])
        issues = [p for p in players_in_frame if p.get("issue_type") and p["issue_type"] != "good_position"]
        if issues:
            lines += ["**本帧问题：**", ""]
            for p in issues:
                itype = ISSUE_TYPE_CN.get(p.get("issue_type", ""), p.get("issue_type", ""))
                note  = p.get("issue_note", "")
                lines.append(f"- **{p['id']}** — {itype}：{note}")
            lines += [""]

    # ── 逐球员详细分析 ────────────────────────────────────────────────────────
    lines += ["---", "", "## 防守球员个人分析", ""]
    player_analysis = data.get("player_analysis", {})

    # 只输出防守球员
    defenders = {k: v for k, v in player_analysis.items() if k.startswith("D")}
    for pid, pa in sorted(defenders.items()):
        rating   = pa.get("overall_rating", "N/A")
        position = pa.get("position", "未知")
        strengths = pa.get("strengths", [])
        issues    = pa.get("issues", [])
        improve   = pa.get("improvement", "")

        lines += [
            f"### {pid} — {position}　评分：{rating} / 10",
            "",
        ]
        if strengths:
            lines += ["**✅ 亮点**", ""]
            for s in strengths:
                lines.append(f"- {s}")
            lines += [""]

        if issues:
            lines += ["**❌ 问题记录**", ""]
            lines += ["| 帧 | 问题类型 | 详细描述 |", "|---|---|---|"]
            for iss in issues:
                fn    = iss.get("frame", "?")
                itype = ISSUE_TYPE_CN.get(iss.get("type", ""), iss.get("type", ""))
                detail = iss.get("detail", "")
                lines.append(f"| Frame {fn} | {itype} | {detail} |")
            lines += [""]

        if improve:
            lines += ["**🎯 训练建议**", "", improve, ""]

        lines += ["---", ""]

    # ── 团队总结 ──────────────────────────────────────────────────────────────
    team_summary = data.get("team_summary", "")
    if team_summary:
        lines += ["## 团队防守总结", "", team_summary, ""]

    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    frame_files = sorted(FRAMES_DIR.glob("frame_*.jpg"))
    if not frame_files:
        print("Error: output/frames/ 下没有找到帧文件，请先运行 coach.py 提取帧")
        return

    print(f"共找到 {len(frame_files)} 帧，开始分析...")
    data = call_gpt4o(frame_files)
    print("  → GPT-4o 分析完成")

    # ── 生成标注图片 ──────────────────────────────────────────────────────────
    annotated_map: dict[str, Path] = {}

    print("生成标注图片...")
    for i, frame_path in enumerate(frame_files, 1):
        fn_key   = str(i)
        finfo    = data.get("frames", {}).get(fn_key, {})
        out_path = ANNOTATED_DIR / frame_path.name
        annotate_frame(frame_path, finfo, out_path)
        annotated_map[fn_key] = out_path
        players = finfo.get("players", [])
        print(f"  → Frame {i:02d} 标注完成（{len(players)} 名球员）")

    # ── 生成报告 ──────────────────────────────────────────────────────────────
    print("生成 Markdown 报告...")
    report_md = generate_report(data, annotated_map)
    REPORT_PATH.write_text(report_md, encoding="utf-8")

    print(f"\n✅ 完成！")
    print(f"   标注图片：{ANNOTATED_DIR}/")
    print(f"   分析报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()
