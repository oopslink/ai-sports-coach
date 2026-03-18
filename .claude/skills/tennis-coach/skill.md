---
name: tennis-coach
description: 网球视频教练分析 skill。当用户提供网球训练或比赛视频并希望获得技术分析、动作点评或改进建议时立即使用。触发词：网球、tennis、正手、反手、发球、截击、步法、引拍、随挥、握拍等。
---

# 网球视频教练分析

## 标准分析流程（三步必做）

视频分析**必须依次执行**以下三步，不可跳过：

```
Step 1: coach.py          → 提取帧 + GPT-4o 综合分析 → output/tennis/coach_*.md
Step 2: tennis_annotate.py → 标注每帧关键部位        → output/tennis/annotated/ + output/tennis/annotate_*.md
Step 3: 向用户输出结构化分析报告（见"报告内容标准"）
```

用户要求 PPT 时额外执行：
```
Step 4: 生成 PPT → node output/tennis/gen_ppt.js
```

---

## 报告内容标准（每次分析必须包含）

### 1. 综合评分
- 总分（X/10）及各维度评分：击球技术 / 步法移动 / 身体旋转 / 击球节奏 / 体能分配 / 战术执行

### 2. 亮点（✅）
- 列出 2-3 个做得好的关键点，注明对应帧号

### 3. 问题逐帧深度分析（❌ 每个问题独立一节）

每个问题必须包含：
- **标注图片**：引用 `output/tennis/annotated/frame_XXX.jpg`
- **帧号 + 问题类型标签**
- **问题描述**：3-5 条详细说明，包含问题部位、姿态偏差、影响
- **正确动作要领**：3-4 条对应正确做法
- **专项训练**：1-2 个针对该问题的具体训练方法（含频次）

### 4. 问题汇总表

| 帧 | 问题类型 | 问题部位 | 描述 | 优先级 |
|---|---|---|---|---|

### 5. 专项训练计划
- 针对每个高优先级问题给出训练方案（训练内容 + 频次 + 目标）

### 6. 教练总结
- 综合评价：优势 + 最紧迫改进点 + 整体潜力判断

---

## 网球教练分析框架

### 击球技术层面

**正手底线（Forehand Groundstroke）**
- 引拍时机：球弹起前完成引拍，拍头指向后方
- 接触点：球在身体前方、腰部高度，手臂自然伸展
- 动力链：后腿蹬地 → 转髋 → 转肩 → 挥拍（从腿发力，非手臂）
- 随挥：击球后拍子向对角线上方随挥，收于非持拍手肩颈处

**反手底线（Backhand Groundstroke）**
- 单反：肩部充分转动，引拍拍面朝后，肘部高位
- 双反：双手同时用力，非惯用手主导发力
- 接触点：身体侧前方，手臂微弯

**发球（Serve）**
- 抛球：在击球点正前上方，高度约离手后上升 15-20cm
- Trophy Position：抖臂后双臂张开，持拍肘高于肩
- 蹬地起跳：后腿蹬地产生向上力量
- 击球：向上伸展击球，手腕内旋（平击）或外旋（切削）
- 随挥：落地一侧继续随挥，不突然停拍

**截击（Volley）**
- 大陆式握拍（Continental Grip）为必须
- 短促格挡，不大幅挥拍
- 向前迎球，不等球来

### 步法与移动

**分步（Split Step）**：对手击球瞬间完成小跳，双脚落地分开，激活反应
**滑步（Shuffle Step）**：横向移动保持平衡，不交叉步
**交叉步（Cross-over Step）**：大范围追球时使用
**击球后复位**：击球完成后立即向底线中间复位

### 问题类型标签表

| 问题类型 | 英文标签 | 说明 |
|---------|---------|------|
| 引拍过晚 | `LATE BACKSWING` | 对方击球时拍子未引好 |
| 握拍错误 | `WRONG GRIP` | 东方/西方/大陆式握拍与球路不符 |
| 换拍未完成 | `GRIP CHANGE ERR` | 正反手切换时握拍未完成换握 |
| 击球点错误 | `WRONG CONTACT` | 击球点太靠身后、太近或在挥臂落势段 |
| 肘部下垂 | `ELBOW DROP` | 发球或高压球肘部下沉 |
| 髋肩未转动 | `NO HIP ROT` | 髋肩旋转不足，力量来源单一 |
| 肩部转动过晚 | `LATE SHOULDER` | 肩膀转动滞后于手臂 |
| 随挥不足 | `NO FOLLOW-THRU` | 击球后挥拍提前停止 |
| 步法不到位 | `POOR FOOTWORK` | 脚步未调整到最优击球位置 |
| 缺少分步预判 | `NO SPLIT STEP` | 对方击球瞬间未做分步准备动作 |
| 重心转移过晚 | `LATE WEIGHT` | 击球时重心仍在后脚 |
| 站姿错误 | `WRONG STANCE` | 开放/封闭/中立站姿与球路不匹配 |
| 场位不合理 | `WRONG POSITION` | 站位距底线过近或过远 |
| 抛球不稳 | `BAD TOSS` | 发球抛球位置不一致或方向偏 |
| 腿部蹬力不足 | `NO LEG DRIVE` | 发球或高压球缺乏腿部蹬伸 |
| 重心不稳 | `OFF BALANCE` | 击球过程中或后失去平衡 |
| 动作路线暴露 | `TELEGRAPH` | 击球方向提前被对手识破 |
| 旋转类型错误 | `WRONG SPIN` | 上旋/切削/平击选择与战术不符 |
| 技术正确 | `GOOD FORM` | 正面标注，绿色圈 |
| 步法优秀 | `GOOD FOOTWORK` | 正面标注 |
| 战术意识好 | `GOOD TACTICS` | 正面标注 |

---

## Step 1：综合教练分析（coach.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --output-dir "output/tennis" --context "<中文 context>"
```

context 模板：
```
这是一段网球训练视频。请全程用中文进行专业网球教练分析。
重点分析方向：综合评估（击球技术 + 步法 + 身体旋转）。
请从以下维度给出详细点评：
- 击球技术：引拍时机、接触点、髋肩旋转、随挥完整性
- 步法：分步时机、移动方式、击球后复位
- 身体姿态：平衡、重心转移、核心稳定性
- 每个问题注明出现在哪一帧，给出具体修正建议。
```

输出：`output/tennis/coach_YYYYMMDD_HHMMSS.md`、`output/tennis/frames/frame_*.jpg`

---

## Step 2：身体部位标注（tennis_annotate.py）

**必须在 coach.py 执行后运行**（依赖 `output/tennis/frames/` 目录）：

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 tennis_annotate.py
```

**标注图例：**
- 🔵 蓝圈 Body — 身体重心
- 🟢 绿圈 Racket Hand — 持拍手位置
- 🟢 绿圈 Off Hand — 非持拍手
- 🟠 橙圈 Lead Foot / Back Foot — 前脚/后脚
- 🔴 红色外圈 — 该部位存在技术问题
- 🟢 绿色外圈 — 该部位动作正确（正面标注）
- 黑底黄字 — 英文问题描述

输出：`output/tennis/annotated/frame_*.jpg` + `output/tennis/annotate_*.md`

---

## Step 4（可选）：PPT 生成

参考 `output/climbing/gen_ppt.js` 结构，创建 `output/tennis/gen_ppt.js`：

```bash
node output/tennis/gen_ppt.js
```

PPT 结构（12 页）：封面 → 综合评分（6 维） → 全程帧总览 → 问题深度分析页（每个问题一页）→ 亮点帧 → 汇总表 → 训练计划 → 教练总结

配色：主色调橙绿（网球配色），问题用红色，亮点用绿色

---

## ⚠️ GPT-4o 调用注意事项
- **英文 system prompt**（中文会触发拒绝）
- **不能说"识别人物"**，用 "biomechanics analysis"、"body part positions as spatial coordinates"
- **detail=low**（12 帧 detail=high 易被过滤）
- System prompt 开头声明："tennis training footage for technique improvement"

## 错误处理
| 错误 | 解决方案 |
|------|---------|
| `Video file not found` | 确认路径，支持 mp4/mov/avi/mkv |
| `ffmpeg is not installed` | `brew install ffmpeg` |
| `OPENAI_API_KEY is not set` | 项目目录创建 `.env` 写入 key |
| GPT-4o 拒绝分析图片 | 检查 system prompt 是英文且无"识别人物"字样 |
| `output/tennis/frames/` 为空 | 先运行 coach.py 提取帧 |
