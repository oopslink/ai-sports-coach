---
name: flag-football-coach
description: 腰旗橄榄球视频教练分析 skill。当用户提供或指定一个腰旗橄榄球视频（mp4/mov/avi 等）并希望获得教练点评、技术分析或改进建议时，立即使用此 skill。即使用户只说"帮我看看这个视频"、"分析一下我的跑位"、"我的传球有什么问题"、"防守复盘"，只要上下文与腰旗橄榄球相关，都应触发。
---

# 腰旗橄榄球视频教练分析

## 分析模式选择

根据用户需求选择合适的分析模式：

| 模式 | 触发场景 | 使用工具 |
|------|---------|---------|
| **综合教练分析** | 全面分析 / 进攻技术 / 团队战术 | `coach.py` |
| **防守专项复盘** | 防守教练视角 / 复盘拔旗/漏人/换防 | `defense_annotate.py` |
| **输出 PPT** | 用户要求幻灯片 | `gen_defense_ppt.js` |
| **输出 PDF** | 用户要求 PDF 报告 | `gen_defense_pdf.py` |

---

## 模式一：综合教练分析（coach.py）

### 第一步：收集信息

依次确认（不要一次问完）：

**1. 视频文件路径**（未提供时询问）

**2. 分析重点**（展示菜单）：
1. 跑位技术 — 路线精准度、启动时机、变向节奏
2. 传球姿势 — QB 握球、步法、出手点、肩膀旋转
3. 接球技术 — 手型、身体对位、脚步落点、抗干扰
4. 拔旗防守 — 预判位置、脚步接近、出手时机
5. 持球跑动 — 护旗意识、变向能力、破防节奏
6. 整体战术 — 阵型配合、时机选择、团队协调
7. 综合评估 — 以上全部

**3. 运动员背景**（选填）：经验水平、场上位置、主要目标

### 第二步：调用 coach.py

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --context "<中文 context>"
```

context 模板：
```
这是一段腰旗橄榄球训练/比赛视频。请全程用中文进行专业教练分析。
重点分析方向：[用户选择]。运动员情况：[背景]。
请从以下维度给出详细点评：动作优点、存在问题（注明出现在哪帧）、具体改进建议。
```

输出：`output/report_YYYYMMDD_HHMMSS.md`，帧在 `output/frames/`

---

## 模式二：防守专项复盘（defense_annotate.py）

### 防守教练复盘框架

复盘时从三个维度分析：

**个人技术**：
- 拔旗：出手时机（提前/滞后）、角度（冲旗/拍旗）、是否被假动作骗过
- 脚步：启动第一步方向、侧移（交叉步 vs 碎步）、追防角度（截断点 vs 身后追）
- 覆盖：1v1 被过路线、有无提前读球

**团队防守**：
- 阵型：开球站位、进攻阵型出现后是否调整
- 换防：交叉跑位时有无喊话换防、有无漏人
- 预判：球传出前有无移动、是否识别对方套路

**帧级溯源**：对每个失误注明帧号、第一个失位球员、失误类型、修正动作

### 调用 defense_annotate.py

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 defense_annotate.py
```

脚本自动读取 `output/frames/`（需先运行 coach.py 提取帧），输出：
- `output/annotated/frame_*.jpg` — 带球员编号标注的图片
- `output/defense_report_YYYYMMDD_HHMMSS.md` — 逐球员分析报告

### 标注规则
- 防守球员：红圈 + `D1/D2...`（按屏幕左→右排序）
- 进攻球员：蓝圈 + `O1/O2...`
- 问题球员：额外黄色警告外圈
- 问题标签（**英文**）：`MISS FLAG` / `FALSE STEP` / `HIGH CENTER` / `LOST MAN` / `NO SWITCH` / `GOOD POS`
- 问题说明（**英文**）：显示在圆圈下方

### ⚠️ GPT-4o 调用注意事项
- **必须用英文 system prompt**（中文 prompt 会触发拒绝）
- **不能说"识别球员"**，要说"spatial/movement analysis"、"position as fractions of image"
- **detail=low**（12 帧 detail=high 会触发内容过滤）
- system prompt 开头声明是"Flag Football training footage for technique improvement"

---

## 模式三：生成 PPT

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
node output/gen_defense_ppt.js
```

输出：`output/defense_report.pptx`

⚠️ **pptxgenjs 必须用全局路径**（`node` 默认找不到全局模块）：
```javascript
const pptxgen = require("/opt/homebrew/lib/node_modules/pptxgenjs");
```

PPT 结构（14 页）：封面 → 综合评分 → 球员图例 → 6 组逐帧标注 → D1/D2 个人分析 → 团队分析 → 训练计划 → 总结

---

## 模式四：生成 PDF

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 output/gen_defense_pdf.py
```

输出：`output/defense_report.pdf`（使用 `reportlab`）

中文字体注册：
```python
pdfmetrics.registerFont(TTFont("CNFont", "/System/Library/Fonts/PingFang.ttc"))
```

⚠️ `ParagraphStyle` 不能在构造时同时用 `fontName=CN_FONT` 作为位置参数和关键字参数，会冲突：
```python
# ❌ 错误
ParagraphStyle(name, fontName=CN_FONT, fontName=CN_FONT)
# ✅ 正确：只在 P() 封装函数里设一次
def P(name, **kw):
    s[name] = ParagraphStyle(name, fontName=CN_FONT, **kw)
P("h1", fontSize=16)  # 不要在 kw 里再传 fontName
```

---

## 报告呈现

分析完成后：
1. 告知用户报告/文件路径
2. 将 Markdown 报告内容直接显示在对话中
3. 标注图片路径提示：在 `output/annotated/` 目录下查看

---

## 错误处理

| 错误 | 解决方案 |
|------|---------|
| `Video file not found` | 确认视频路径 |
| `ffmpeg is not installed` | `brew install ffmpeg` |
| `OPENAI_API_KEY is not set` | 项目目录创建 `.env` 填入 Key |
| `unsupported video format` | 支持：.mp4 .mov .avi .mkv .webm |
| GPT-4o 返回"无法分析图片" | 检查 system prompt 是否为英文且无"识别/identify person"字样 |
| `Cannot find module 'pptxgenjs'` | 用全局绝对路径 require |
| `multiple values for fontName` | 见 PDF 注意事项，不要重复传 fontName |

---

## 注意事项

- 视频建议 10–120 秒，超长视频截取 12 帧，精度下降
- 多段视频每段单独运行 coach.py，分别生成帧和报告
- `defense_annotate.py` 依赖已有的 `output/frames/`，必须先跑 coach.py
- 标注文字统一用**英文**，PIL 默认字体不支持中文，强制英文可避免乱码
