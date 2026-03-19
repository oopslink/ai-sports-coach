// 网球教练分析 PPT 生成脚本
const pptxgen = require("/opt/homebrew/lib/node_modules/pptxgenjs");
const path = require("path");
const fs = require("fs");

const OUT_DIR = __dirname;
const ANNOTATED = path.join(OUT_DIR, "annotated");
const FRAMES = path.join(OUT_DIR, "frames");

const af = (n) => path.join(ANNOTATED, `frame_${String(n).padStart(3, "0")}.jpg`);
const rf = (n) => path.join(FRAMES, `frame_${String(n).padStart(3, "0")}.jpg`);
const frameExists = (p) => fs.existsSync(p);

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "网球教练技术分析报告";

// ── 配色（网球主题：橙绿）────────────────────────────────────────────────────
const C = {
  court:   "2D6A2D",   // 深网球绿
  green:   "4CAF50",   // 亮绿
  lime:    "8BC34A",   // 黄绿
  orange:  "FF6F00",   // 网球橙
  amber:   "FFA000",   // 琥珀
  yellow:  "F9A825",   // 网球黄
  red:     "D32F2F",   // 问题红
  blue:    "1976D2",   // 信息蓝
  white:   "FFFFFF",
  light:   "F5F7F0",   // 浅绿白
  gray:    "757575",
  dark:    "212121",
  redBg:   "FFF3F3",
  greenBg: "F1F8E9",
  courtBg: "E8F5E9",
};

const makeShadow = () => ({ type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.12 });

// ── 辅助：页眉 ────────────────────────────────────────────────────────────────
function addHeader(slide, title, accent) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.court }, line: { color: C.court },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.9, w: 10, h: 0.07, fill: { color: accent || C.yellow }, line: { color: accent || C.yellow },
  });
  slide.addText(title, {
    x: 0.5, y: 0.1, w: 9, h: 0.68, fontSize: 22, bold: true, color: C.white, margin: 0,
  });
}

// ── 辅助：评分环 ──────────────────────────────────────────────────────────────
function addScoreBadge(slide, score, x, y, label) {
  const col = score >= 8 ? C.green : score >= 6 ? C.amber : C.red;
  slide.addShape(pres.shapes.OVAL, { x, y, w: 1.3, h: 1.3, fill: { color: col }, line: { color: col } });
  slide.addText(`${score}`, { x, y: y + 0.05, w: 1.3, h: 0.75, fontSize: 36, bold: true, color: C.white, align: "center", margin: 0 });
  slide.addText("/10", { x, y: y + 0.72, w: 1.3, h: 0.35, fontSize: 12, color: C.white, align: "center", margin: 0 });
  if (label) {
    slide.addText(label, { x: x - 0.1, y: y + 1.35, w: 1.5, h: 0.3, fontSize: 11, color: C.gray, align: "center", margin: 0 });
  }
}

// ── 辅助：问题标签条 ──────────────────────────────────────────────────────────
function addIssueBadge(slide, label, x, y, w) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.33, fill: { color: C.red }, line: { color: C.red } });
  slide.addText(`⚠ ${label}`, { x: x + 0.08, y, w: w - 0.1, h: 0.33, fontSize: 11, bold: true, color: C.white, valign: "middle", margin: 0 });
}

// ── 辅助：好评标签条 ──────────────────────────────────────────────────────────
function addGoodBadge(slide, label, x, y, w) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.33, fill: { color: C.green }, line: { color: C.green } });
  slide.addText(`✓ ${label}`, { x: x + 0.08, y, w: w - 0.1, h: 0.33, fontSize: 11, bold: true, color: C.white, valign: "middle", margin: 0 });
}

// ── 辅助：分析卡片 ────────────────────────────────────────────────────────────
function addAnalysisCard(slide, x, y, w, h, title, titleColor, items) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: C.white }, line: { color: "DCE3EC" }, shadow: makeShadow(),
  });
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.06, h, fill: { color: titleColor }, line: { color: titleColor } });
  slide.addText(title, { x: x + 0.15, y: y + 0.08, w: w - 0.25, h: 0.36, fontSize: 13, bold: true, color: titleColor, margin: 0 });
  items.forEach((item, i) => {
    slide.addText(`• ${item}`, {
      x: x + 0.2, y: y + 0.48 + i * 0.42, w: w - 0.35, h: 0.38,
      fontSize: 11, color: C.dark, margin: 0,
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 1 — 封面
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.court };

  if (frameExists(af(5))) {
    slide.addImage({ path: af(5), x: 5.2, y: 0, w: 4.8, h: 5.625, transparency: 25 });
  }
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.0, y: 0, w: 5.0, h: 5.625, fill: { color: C.court, transparency: 35 }, line: { color: C.court, transparency: 35 },
  });

  // 顶部装饰线（网球黄）
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.12, fill: { color: C.yellow }, line: { color: C.yellow } });

  slide.addText("网球", { x: 0.5, y: 0.5, w: 5.2, h: 0.72, fontSize: 38, bold: true, color: C.yellow, margin: 0 });
  slide.addText("教练技术分析报告", { x: 0.5, y: 1.2, w: 5.2, h: 0.65, fontSize: 28, bold: true, color: C.white, margin: 0 });

  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 2.0, w: 4.0, h: 0.06, fill: { color: C.orange }, line: { color: C.orange } });
  slide.addText("逐帧标注 · 问题深度剖析 · 专项训练方案", {
    x: 0.5, y: 2.18, w: 5.0, h: 0.42, fontSize: 13, color: "C8E6C9", italic: true, margin: 0,
  });

  [
    ["分析日期", "2026-03-19"],
    ["视频文件", "tennis.mp4"],
    ["综合评分", "7 / 10"],
    ["发现问题", "引拍过晚 · 击球点偏差 · 随挥不足 · 站姿不合理"],
  ].forEach(([k, v], i) => {
    slide.addText([
      { text: `${k}：`, options: { bold: true, color: C.yellow } },
      { text: v, options: { color: "C8E6C9" } },
    ], { x: 0.5, y: 3.25 + i * 0.45, w: 5.5, h: 0.38, fontSize: 12.5, margin: 0 });
  });

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.43, w: 10, h: 0.195, fill: { color: C.yellow, transparency: 20 }, line: { color: C.yellow, transparency: 20 } });
  slide.addText("AI Sports Coach · 网球技术分析系统", {
    x: 0.5, y: 5.43, w: 9, h: 0.195, fontSize: 9, color: C.white, align: "center", valign: "middle", margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 2 — 综合评分总览
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "综合技术评分总览", C.yellow);

  addScoreBadge(slide, 7, 4.35, 1.05, "综合评分");

  const dims = [
    { label: "击球技术", score: 6, color: C.amber },
    { label: "步法移动", score: 6, color: C.amber },
    { label: "身体旋转", score: 6, color: C.amber },
    { label: "击球节奏", score: 7, color: C.blue },
    { label: "体能分配", score: 7, color: C.blue },
    { label: "战术执行", score: 7, color: C.blue },
  ];

  dims.forEach((d, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.4 + col * 4.8;
    const y = 2.95 + row * 0.75;

    slide.addText(d.label, { x, y, w: 1.7, h: 0.55, fontSize: 12, bold: true, color: C.dark, valign: "middle", margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, { x: x + 1.75, y: y + 0.1, w: 3.0, h: 0.35, fill: { color: "E8ECF0" }, line: { color: "E8ECF0" } });
    slide.addShape(pres.shapes.RECTANGLE, { x: x + 1.75, y: y + 0.1, w: (d.score / 10) * 3.0, h: 0.35, fill: { color: d.color }, line: { color: d.color } });
    slide.addText(`${d.score}`, { x: x + 4.82, y, w: 0.38, h: 0.55, fontSize: 13, bold: true, color: d.color, align: "center", valign: "middle", margin: 0 });
  });

  slide.addText("🟡 橙色需提升　🔵 蓝色已达标　🔴 红色重点改进", {
    x: 0.4, y: 5.1, w: 9.2, h: 0.32, fontSize: 11, color: C.gray, align: "center", margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 3 — 全程帧总览（12帧，问题帧高亮）
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.light };
  addHeader(slide, "全程关键帧总览（红框 = 问题帧）", C.yellow);

  const problemFrames = new Set([3, 5, 6, 12]);
  const problemLabels = { 3: "引拍过晚", 5: "击球点↗", 6: "随挥不足", 12: "站姿错误" };
  const cols = 6, fw = 1.5, fh = 1.12;
  const startX = 0.25, startY = 1.1;
  const gapX = 0.1, gapY = 0.15;

  for (let i = 0; i < 12; i++) {
    const fn = i + 1;
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = startX + col * (fw + gapX);
    const y = startY + row * (fh + 0.55 + gapY);
    const isProblem = problemFrames.has(fn);

    if (frameExists(af(fn))) {
      slide.addImage({ path: af(fn), x, y, w: fw, h: fh });
    } else {
      slide.addShape(pres.shapes.RECTANGLE, { x, y, w: fw, h: fh, fill: { color: "E0E0E0" }, line: { color: "CCC" } });
    }

    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w: fw, h: fh,
      fill: { color: "FFFFFF", transparency: 100 },
      line: { color: isProblem ? C.red : "CCCCCC", pt: isProblem ? 2.5 : 0.75 },
    });

    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: y + fh, w: fw, h: 0.27,
      fill: { color: isProblem ? C.red : C.court }, line: { color: isProblem ? C.red : C.court },
    });
    slide.addText(`F${String(fn).padStart(2, "0")}${isProblem ? " ⚠" : ""}`, {
      x, y: y + fh, w: fw, h: 0.27, fontSize: 10, bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });

    if (isProblem) {
      slide.addText(problemLabels[fn] || "", {
        x, y: y + fh + 0.28, w: fw, h: 0.25, fontSize: 9, color: C.red, bold: true, align: "center", margin: 0,
      });
    }
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 4 — 问题深度分析：引拍过晚（Frame 3）
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "【击球技术问题深度分析】LATE BACKSWING — Frame 3", C.red);

  if (frameExists(af(3))) {
    slide.addImage({ path: af(3), x: 0.3, y: 1.1, w: 4.2, h: 4.0 });
  }
  addIssueBadge(slide, "Frame 03 — 引拍动作迟缓，步法被打乱", 0.3, 1.1, 4.2);

  addAnalysisCard(slide, 4.8, 1.1, 4.9, 1.68, "问题描述", C.red, [
    "对方击球时引拍尚未完成，回摆时机明显滞后",
    "引拍迟缓导致步法跟进出现犹豫，节奏被打乱",
    "前脚落地有停顿感，整体动作链不够流畅",
    "被动引拍压缩击球准备时间，影响接触点质量",
  ]);

  addAnalysisCard(slide, 4.8, 2.86, 4.9, 1.42, "正确动作要领", C.green, [
    "判断来球落点瞬间（对方击球后）立即引拍",
    "拍头指向身体后方，与肩部齐平或略高",
    "引拍同时完成分步（split step），保持弹性预判",
    "引拍完成后静待球进入最佳击球区",
  ]);

  addAnalysisCard(slide, 4.8, 4.35, 4.9, 1.1, "专项训练", C.court, [
    "Shadow Swing：无球模拟判断→引拍流程，20次/组×3组/天",
    "快节奏喂球：要求球弹起前完成引拍，30球/组",
  ]);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 5 — 问题深度分析：击球点偏差（Frame 5）
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "【击球技术问题深度分析】WRONG CONTACT — Frame 5", C.red);

  if (frameExists(af(5))) {
    slide.addImage({ path: af(5), x: 0.3, y: 1.1, w: 4.2, h: 4.0 });
  }
  addIssueBadge(slide, "Frame 05 — 拍面接触点偏后偏内，力量损失", 0.3, 1.1, 4.2);

  addAnalysisCard(slide, 4.8, 1.1, 4.9, 1.68, "问题描述", C.red, [
    "拍面与球接触位置偏离理想点，球路偏差",
    "击球点偏后或偏内，手臂未充分伸展即接球",
    "接触点偏差直接降低拍面控制精度和力量",
    "击球时拍头未完全对准来球轨迹，旋转不稳定",
  ]);

  addAnalysisCard(slide, 4.8, 2.86, 4.9, 1.42, "正确动作要领", C.green, [
    "接触点在身体右前方约一臂伸展处（正手）",
    "球的高度控制在腰部至胸部之间",
    "接触瞬间手腕保持稳定，不过早释放腕力",
    "转髋同步完成，确保动力链传导到拍面",
  ]);

  addAnalysisCard(slide, 4.8, 4.35, 4.9, 1.1, "专项训练", C.court, [
    "定点击球桩训练：固定球位反复练习正确接触感，100次/天",
    "镜前慢动作练习：观察接触点是否在身体正前方",
  ]);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 6 — 问题深度分析：随挥不足（Frame 6）
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "【击球技术问题深度分析】NO FOLLOW-THROUGH — Frame 6", C.red);

  if (frameExists(af(6))) {
    slide.addImage({ path: af(6), x: 0.3, y: 1.1, w: 4.2, h: 4.0 });
  }
  addIssueBadge(slide, "Frame 06 — 击球后随挥提前停止，旋转不稳", 0.3, 1.1, 4.2);

  addAnalysisCard(slide, 4.8, 1.1, 4.9, 1.68, "问题描述", C.red, [
    "击球后拍子过早减速，随挥动作提前终止",
    "未完成至非持拍手肩颈处的完整随挥弧线",
    "随挥不足导致旋转量不稳定，上旋球质量下降",
    "提前收拍在接触点前形成减速，实际降低击球力量",
  ]);

  addAnalysisCard(slide, 4.8, 2.86, 4.9, 1.42, "正确动作要领", C.green, [
    "击球后拍面沿击球方向继续向对角线上方推送",
    "最终收拍于非持拍手一侧肩颈位置（正手标准位）",
    "整个随挥过程保持手腕和前臂的自然内旋",
    "随挥结束后立即恢复备战姿势",
  ]);

  addAnalysisCard(slide, 4.8, 4.35, 4.9, 1.1, "专项训练", C.court, [
    "完整随挥慢速练习：降低击球速度，专注随挥到位，20球/组",
    "随挥+复位连贯练习：完成随挥后立即滑步复位，15次/组",
  ]);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 7 — 问题深度分析：站姿不合理（Frame 12）
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "【步法问题深度分析】WRONG STANCE — Frame 12", C.amber);

  if (frameExists(af(12))) {
    slide.addImage({ path: af(12), x: 0.3, y: 1.1, w: 4.2, h: 4.0 });
  }
  addIssueBadge(slide, "Frame 12 — 击球后未回中位，被动应招下一拍", 0.3, 1.1, 4.2);

  addAnalysisCard(slide, 4.8, 1.1, 4.9, 1.68, "问题描述", C.amber, [
    "击球完成后站姿未还原到备战中位，前脚落点欠佳",
    "姿势偏向一侧，覆盖角度受限",
    "脚步未完成二次调整，不利于快速启动移动",
    "可能影响下一拍分步时机，形成连续被动局面",
  ]);

  addAnalysisCard(slide, 4.8, 2.86, 4.9, 1.42, "正确动作要领", C.green, [
    "每次击球完成随挥后立即完成 1-2 步中位复位",
    "备战站姿：双脚与肩同宽，重心微压前脚掌，双膝微屈",
    "保持在底线中心线附近，覆盖两角机会球",
    "非持拍手轻托拍喉，保持随时可引拍的预备状态",
  ]);

  addAnalysisCard(slide, 4.8, 4.35, 4.9, 1.1, "专项训练", C.court, [
    "击球-复位连续训练：每次击球后立刻 shuffle step 回中位",
    "五点跑步法训练：底线五点快速移动，强化中位意识",
  ]);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 8 — 亮点帧展示
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "亮点帧展示 — 技术执行正确的关键时刻", C.lime);

  const goodFrames = [
    { fn: 1, note: "引拍时机好，初期准备到位" },
    { fn: 2, note: "平衡感强，重心稳定" },
    { fn: 8, note: "击球后主动复位意识良好" },
    { fn: 10, note: "备战姿态稳定，节奏感好" },
  ];

  goodFrames.forEach((g, i) => {
    const x = 0.3 + i * 2.38;
    if (frameExists(af(g.fn))) {
      slide.addImage({ path: af(g.fn), x, y: 1.1, w: 2.2, h: 3.3 });
    }
    addGoodBadge(slide, `Frame ${String(g.fn).padStart(2, "0")}`, x, 1.1, 2.2);
    slide.addText(g.note, {
      x, y: 4.48, w: 2.2, h: 0.55, fontSize: 10.5, color: C.dark, align: "center", italic: true, margin: 0,
    });
  });

  slide.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 5.1, w: 9.4, h: 0.38, fill: { color: C.greenBg }, line: { color: "A9DFBF" } });
  slide.addText("✅ 引拍时机与平衡感构成扎实基础——将这种稳定性延伸至击球全链路是下阶段核心目标", {
    x: 0.4, y: 5.1, w: 9.2, h: 0.38, fontSize: 11.5, color: C.court, bold: true, valign: "middle", margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 9 — 问题汇总对照表
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "全部问题汇总对照表", C.orange);

  slide.addTable([
    [
      { text: "帧", options: { bold: true, fill: { color: C.court }, color: C.white, fontSize: 12, align: "center" } },
      { text: "问题类型", options: { bold: true, fill: { color: C.court }, color: C.white, fontSize: 12 } },
      { text: "问题部位", options: { bold: true, fill: { color: C.court }, color: C.white, fontSize: 12 } },
      { text: "描述", options: { bold: true, fill: { color: C.court }, color: C.white, fontSize: 12 } },
      { text: "优先级", options: { bold: true, fill: { color: C.court }, color: C.white, fontSize: 12, align: "center" } },
    ],
    [
      { text: "F03", options: { align: "center", bold: true } },
      { text: "引拍过晚  LATE BACKSWING", options: { color: C.red } },
      "身体重心 / 前脚",
      "回摆迟缓导致步法被动，节奏被打乱",
      { text: "高", options: { align: "center", bold: true, color: C.red } },
    ],
    [
      { text: "F05", options: { align: "center", bold: true } },
      { text: "击球点错误  WRONG CONTACT", options: { color: C.red } },
      "持拍手 / 拍面",
      "接触点偏后偏内，手臂未充分伸展，力量损失",
      { text: "高", options: { align: "center", bold: true, color: C.red } },
    ],
    [
      { text: "F06", options: { align: "center", bold: true } },
      { text: "随挥不足  NO FOLLOW-THRU", options: { color: C.red } },
      "持拍手 / 前臂",
      "击球后拍子过早停止，上旋旋转量不稳定",
      { text: "高", options: { align: "center", bold: true, color: C.red } },
    ],
    [
      { text: "F12", options: { align: "center", bold: true } },
      { text: "站姿错误  WRONG STANCE", options: { color: C.amber } },
      "前脚 / 身体重心",
      "击球后未回中位，覆盖角度受限，被动应招",
      { text: "中", options: { align: "center", bold: true, color: C.amber } },
    ],
  ], {
    x: 0.3, y: 1.1, w: 9.4, h: 3.5,
    fontSize: 11,
    border: { pt: 0.5, color: "DCE3EC" },
    rowH: 0.7,
  });

  slide.addText("优先级「高」= 直接影响击球质量和比赛稳定性，建议立即针对性训练", {
    x: 0.3, y: 4.75, w: 9.4, h: 0.32, fontSize: 11, color: C.gray, italic: true, align: "center", margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 10 — 专项训练计划
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.light };
  addHeader(slide, "专项训练改进计划", C.lime);

  const plans = [
    {
      num: "01", priority: "高", priColor: C.red, target: "引拍时机",
      title: "Shadow Swing + 快节奏喂球训练",
      detail: "无球模拟来球判断→引拍完整流程，建立「对方击球即引拍」的条件反射；结合教练快节奏喂球，要求球弹起前完成引拍，专注时机而非力量。",
      freq: "每次训练开始热身 15 分钟，持续 3 周",
    },
    {
      num: "02", priority: "高", priColor: C.red, target: "击球点",
      title: "定点击球桩 + 低速喂球定位练习",
      detail: "将网球固定在特定位置反复击打，建立身体前方一臂处接触球的肌肉记忆；配合低速喂球定点正手，教练确认每球接触点位置。",
      freq: "每次训练 100 次固定点击球，持续 2 周",
    },
    {
      num: "03", priority: "高", priColor: C.red, target: "随挥完整性",
      title: "慢速随挥专项 + 随挥-复位连贯训练",
      detail: "降低击球速度，专注每次击球随挥到肩颈位置，逐步提速；完成随挥后立即 shuffle step 复位至底线中位，将随挥与复位做成连贯动作。",
      freq: "每次训练 30 球慢速随挥，逐步加速",
    },
    {
      num: "04", priority: "中", priColor: C.amber, target: "击球后复位",
      title: "击球-复位连续训练 + 五点跑步法",
      detail: "每次击球后立刻做 shuffle step 复位至中位，等待下一球喂入，强化条件反射；五点跑步法训练底线快速移动，提升中位覆盖意识和启动速度。",
      freq: "每次训练综合练习段，每组 20 球",
    },
  ];

  plans.forEach((p, i) => {
    const y = 1.05 + i * 0.98;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y, w: 9.4, h: 0.88, fill: { color: C.white }, line: { color: "DCE3EC" }, shadow: makeShadow(),
    });
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 0.62, h: 0.88, fill: { color: C.court }, line: { color: C.court } });
    slide.addText(p.num, { x: 0.3, y, w: 0.62, h: 0.88, fontSize: 18, bold: true, color: C.yellow, align: "center", valign: "middle", margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, { x: 9.1, y: y + 0.08, w: 0.55, h: 0.28, fill: { color: p.priColor }, line: { color: p.priColor } });
    slide.addText(`${p.priority}`, { x: 9.1, y: y + 0.08, w: 0.55, h: 0.28, fontSize: 9, bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, { x: 7.72, y: y + 0.08, w: 1.3, h: 0.28, fill: { color: C.courtBg }, line: { color: "88C88A" } });
    slide.addText(p.target, { x: 7.72, y: y + 0.08, w: 1.3, h: 0.28, fontSize: 9, color: C.court, align: "center", valign: "middle", margin: 0 });
    slide.addText(p.title, { x: 1.02, y: y + 0.05, w: 6.5, h: 0.32, fontSize: 12, bold: true, color: C.dark, margin: 0 });
    slide.addText(`${p.detail}　【${p.freq}】`, { x: 1.02, y: y + 0.42, w: 6.5, h: 0.4, fontSize: 10, color: C.gray, margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 11 — 教练总结
// ══════════════════════════════════════════════════════════════════════════════
{
  const slide = pres.addSlide();
  slide.background = { color: C.court };

  if (frameExists(af(2))) {
    slide.addImage({ path: af(2), x: 0, y: 0, w: 10, h: 5.625, transparency: 72 });
  }
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.court, transparency: 15 }, line: { color: C.court, transparency: 15 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.12, fill: { color: C.yellow }, line: { color: C.yellow } });

  slide.addText("教练综合总结", { x: 0.6, y: 0.22, w: 9, h: 0.45, fontSize: 13, bold: true, color: C.yellow, margin: 0 });
  slide.addText("技术评估结论", { x: 0.6, y: 0.68, w: 8, h: 0.62, fontSize: 28, bold: true, color: C.white, margin: 0 });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.38, w: 3.5, h: 0.06, fill: { color: C.yellow }, line: { color: C.yellow } });

  const points = [
    ["✅ 核心亮点", C.lime,   "引拍时机合理，重心平衡感出色，击球后有主动复位意识，基本功扎实。"],
    ["❌ 首要问题", C.red,    "击球链三环节（引拍→接触点→随挥）均有缺失，需系统性重建正手动作路径。"],
    ["⚠ 改进重点", C.yellow, "慢速+大量重复重塑肌肉记忆，4-6 周专项训练后击球质量可显著提升。"],
    ["→ 总体评价", "C8E6C9", "潜力中上，步法战术意识已具备基础，技术链完整化后有望快速提升至 8.5/10。"],
  ];

  points.forEach((p, i) => {
    slide.addText([
      { text: `${p[0]}  `, options: { bold: true, color: p[1] } },
      { text: p[2], options: { color: "C8E6C9" } },
    ], { x: 0.7, y: 1.6 + i * 0.65, w: 8.5, h: 0.55, fontSize: 13, margin: 0 });
  });

  addScoreBadge(slide, 7, 8.4, 1.5);

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.4, w: 10, h: 0.225, fill: { color: C.yellow, transparency: 20 }, line: { color: C.yellow, transparency: 20 } });
  slide.addText("AI Sports Coach · 网球技术分析 · 2026-03-19", {
    x: 0.5, y: 5.4, w: 9, h: 0.225, fontSize: 9, color: C.white, align: "center", valign: "middle", margin: 0,
  });
}

// ── 输出 ──────────────────────────────────────────────────────────────────────
const outPath = path.join(OUT_DIR, "report.pptx");
pres.writeFile({ fileName: outPath })
  .then(() => console.log(`✅ PPT 已生成：${outPath}`))
  .catch((e) => { console.error("PPT 生成失败:", e); process.exit(1); });
