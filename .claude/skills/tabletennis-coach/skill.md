---
name: tabletennis-coach
description: 乒乓球视频教练分析 skill。当用户提供乒乓球训练或比赛视频并希望获得技术分析时立即使用。触发词：乒乓球、table tennis、正手、反手、弧圈、发球、步法、旋转、拉球、推挡等。
---

# 乒乓球视频教练分析

## 标准分析流程（三步必做）

```
Step 1: coach.py               → 提取帧 + GPT-4o 综合分析 → output/tabletennis/coach_*.md
Step 2: tabletennis_annotate.py → 标注每帧关键部位         → output/tabletennis/annotated/ + output/tabletennis/annotate_*.md
Step 3: 向用户输出结构化分析报告
```

用户要求 PPT 时：`node output/tabletennis/gen_ppt.js`

---

## 报告内容标准（每次分析必须包含）

### 1. 综合评分（X/10）
维度：正反手技术 / 步法节奏 / 身体旋转 / 发球变化 / 接发球 / 台内控制

### 2. 亮点（✅）— 2-3 个，注明帧号

### 3. 问题逐帧深度分析（❌ 每个问题独立一节）
- **标注图片**：`output/tabletennis/annotated/frame_XXX.jpg`
- **帧号 + 问题类型标签**
- **问题描述**：3-5 条
- **正确动作要领**：3-4 条
- **专项训练**：1-2 个（含频次）

### 4. 问题汇总表 | 5. 专项训练计划 | 6. 教练总结

---

## 乒乓球教练分析框架

### 击球技术

**正手拉球（Forehand Loop）**
- 引拍：拍头向下，置于右腰侧（右手持拍），拍面稍关闭
- 触球方式：从球的后下方向前上方摩擦，制造强上旋
- 腰腿发力：腰部转动 → 前臂加速 → 手腕收拍，三段发力
- 随挥：拍子随挥至额头左侧，不提前停拍

**反手弧圈（Backhand Loop）**
- 引拍：肘部内收，拍置于腹部左侧
- 发力：以肘为轴，前臂向前上方加速
- 手腕内旋：触球瞬间手腕内旋增加旋转量
- 重心：由左腿转至右腿（右手选手）

**发球**
- 抛球高度：必须 16cm 以上（规则要求）
- 接触点：在台面上方的有效位置
- 旋转变化：下旋 / 侧旋 / 上旋 / 不转变化混用

**防守反击**
- 挡球：拍面稍开，借力回击
- 推挡：腰腿固定，前臂向前推送

### 步法

**小碎步（Quick Shuffle）**：近台快速微调，频率高幅度小
**侧滑步（Side Slide）**：横向大范围移动
**交叉步（Cross-over）**：大范围追球必用
**并步**：前后调整站位距离

### 问题类型标签表

| 问题类型 | 英文标签 | 说明 |
|---------|---------|------|
| 反应过慢 | `LATE REACT` | 来球到达时未提前到位 |
| 引拍过晚 | `LATE BACKSWING` | 球拍未在来球前引好 |
| 缺乏躯干旋转 | `NO ROTATION` | 躯干未转动，纯手臂打球 |
| 肘部位置错误 | `HIGH ELBOW` | 肘部抬高或过低导致动作变形 |
| 肘部过于内收 | `ELBOW TOO CLOSE` | 肘部紧贴身体，限制挥拍幅度 |
| 手腕未加速收拍 | `NO WRIST SNAP` | 拉球时手腕未在触球点爆发加速 |
| 拍面角度错误 | `BAD BAT ANGLE` | 触球时拍面过开或过闭 |
| 随挥不足 | `NO FOLLOW-THRU` | 击球后球拍未完成随挥 |
| 握拍错误 | `WRONG GRIP` | 握拍过紧或握拍姿势错误 |
| 站位错误 | `WRONG STANCE` | 站位过直、离台过远/过近 |
| 步法不到位 | `POOR FOOTWORK` | 击球时步法未调整到位 |
| 缺少侧步转髋 | `NO PIVOT STEP` | 拉球时未做转髋侧步蓄力 |
| 未用交叉步追球 | `NO CROSS STEP` | 大角度来球只侧滑而未交叉步 |
| 台内短球处理差 | `POOR SHORT GAME` | 台内球触碰感差，处理失误多 |
| 弧圈球弧度错误 | `WRONG LOOP ARC` | 拉球弧度过平或过高，落点不稳 |
| 发球旋转变化不足 | `POOR SERVE SPIN` | 发球旋转单一，易被对方预判 |
| 准备姿势不规范 | `WRONG READY POS` | 回合间持拍姿势错误 |
| 技术选择错误 | `WRONG SELECTION` | 对特定来球选择了错误技术 |
| 技术正确 | `GOOD FORM` | 正面标注，绿色圈 |
| 步法优秀 | `GOOD FOOTWORK` | 正面标注 |
| 发球质量高 | `GOOD SERVE` | 正面标注 |

---

## Step 1：综合教练分析（coach.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --output-dir "output/tabletennis" --context "这是一段乒乓球训练视频。请全程用中文进行专业乒乓球教练分析。综合评估：正反手技术、步法节奏、身体旋转、发球接发球。重点关注：腰腿发力是否充分、手腕是否有效加速、步法是否及时到位。每个问题注明帧号，给出具体修正建议。"
```

输出：`output/tabletennis/coach_*.md`、`output/tabletennis/frames/`

---

## Step 2：部位标注（tabletennis_annotate.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 tabletennis_annotate.py
```

标注：Body（重心）/ Racket Hand（持拍手）/ Free Hand（自由手）/ Lead Foot / Back Foot
输出：`output/tabletennis/annotated/` + `output/tabletennis/annotate_*.md`

---

## ⚠️ GPT-4o 调用注意事项
- 英文 system prompt，不提识别人物，用 biomechanics analysis，detail=low
- System prompt 声明："table tennis training footage for technique improvement"
