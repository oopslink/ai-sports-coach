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
FRAMES_DIR   = Path("output/frames")
ANNOTATED_DIR = Path("output/annotated")
REPORT_PATH  = Path(f"output/defense_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

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


def call_gpt4o(frames: list[Path]) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)

    content: list[dict] = [
        {"type": "text", "text": f"以下是腰旗橄榄球比赛视频的 {len(frames)} 帧截图，请按要求分析："}
    ]
    for i, frame in enumerate(frames, 1):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image(frame)}",
                "detail": "low",
            },
        })
        content.append({"type": "text", "text": f"[Frame {i}]"})

    print("  → 发送帧到 GPT-4o（detail=low）...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        max_tokens=4000,
    )

    raw = response.choices[0].message.content
    # 去掉可能的 markdown 包裹
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # 尝试提取 JSON 块
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise RuntimeError(f"JSON 解析失败:\n{raw}") from e


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


def draw_label(draw: ImageDraw.ImageDraw, text: str, cx: int, cy: int,
               bg: tuple, fg: tuple, font, padding: int = 4):
    """在 (cx, cy) 正上方画一个带背景的标签。"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x0 = cx - tw // 2 - padding
    y0 = cy - th - padding * 2 - 4   # 放在圆圈上方
    x1 = cx + tw // 2 + padding
    y1 = cy - 4
    draw.rectangle([x0, y0, x1, y1], fill=bg)
    draw.text((x0 + padding, y0 + padding), text, font=font, fill=fg)


def draw_issue_note(draw: ImageDraw.ImageDraw, note: str, cx: int, cy: int,
                    img_w: int, img_h: int, font_small):
    """在球员圆圈下方画问题说明文字（自动换行，最多 2 行）。"""
    max_chars = 14
    lines = textwrap.wrap(note, max_chars)[:2]
    y_offset = cy + 45
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_small)
        tw = bbox[2] - bbox[0]
        tx = max(4, min(cx - tw // 2, img_w - tw - 4))
        draw.rectangle([tx - 2, y_offset - 1, tx + tw + 2, y_offset + 16], fill=(30, 30, 30, 180))
        draw.text((tx, y_offset), line, font=font_small, fill=(255, 230, 100))
        y_offset += 17


ISSUE_ICONS = {
    "missed_flag":    "MISS FLAG",
    "false_step":     "FALSE STEP",
    "high_center":    "HIGH CENTER",
    "lost_coverage":  "LOST MAN",
    "no_switch":      "NO SWITCH",
    "good_position":  "GOOD POS",
}


def annotate_frame(frame_path: Path, players: list[dict], out_path: Path):
    img = Image.open(frame_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    W, H = img.size
    font_label = get_font(18)
    font_issue = get_font(13)

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
        # 球员编号标签
        icon = ISSUE_ICONS.get(issue_type, "")
        label = f"{pid}" + (f" {icon}" if icon else "")
        draw_label(draw, label, cx, cy, bg=lbg + (210,), fg=COLOR["label_fg"], font=font_label)

        # 问题说明文字
        if issue_note and is_issue:
            draw_issue_note(draw, issue_note, cx, cy, W, H, font_issue)

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
        rel_path = img_path.relative_to(Path("output"))
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
    frame_data = data.get("frames", {})
    annotated_map: dict[str, Path] = {}

    print("生成标注图片...")
    for i, frame_path in enumerate(frame_files, 1):
        fn_key = str(i)
        finfo  = frame_data.get(fn_key, {})
        players = finfo.get("players", [])

        out_path = ANNOTATED_DIR / frame_path.name
        annotate_frame(frame_path, players, out_path)
        annotated_map[fn_key] = out_path
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
