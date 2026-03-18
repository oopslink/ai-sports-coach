---
name: badminton-coach
description: 羽毛球视频教练分析 skill。当用户提供羽毛球训练或比赛视频并希望获得技术分析时立即使用。触发词：羽毛球、badminton、扣杀、高远球、网前、步法、手腕、发球、反手、握拍等。
---

# 羽毛球视频教练分析

## 标准分析流程（三步必做）

```
Step 1: coach.py              → 提取帧 + GPT-4o 综合分析 → output/badminton/coach_*.md
Step 2: badminton_annotate.py → 标注每帧关键部位          → output/badminton/annotated/ + output/badminton/annotate_*.md
Step 3: 向用户输出结构化分析报告
```

用户要求 PPT 时：`node output/badminton/gen_ppt.js`

---

## 报告内容标准（每次分析必须包含）

### 1. 综合评分（X/10）
维度：扣杀技术 / 步法移动 / 击球节奏 / 网前技术 / 发球接发 / 回位意识

### 2. 亮点（✅）— 2-3 个，注明帧号

### 3. 问题逐帧深度分析（❌ 每个问题独立一节）
- **标注图片**：`output/badminton/annotated/frame_XXX.jpg`
- **帧号 + 问题类型标签**
- **问题描述**：3-5 条
- **正确动作要领**：3-4 条
- **专项训练**：1-2 个（含频次）

### 4. 问题汇总表 | 5. 专项训练计划 | 6. 教练总结

---

## 羽毛球教练分析框架

### 击球技术

**高远球（Clear）**
- 击球点：身体前上方，手臂充分伸展的最高点
- 挥拍轨迹：从后下方向前上方弧线发力
- 手腕外旋（前旋）：击球瞬间手腕迅速外旋（旋前）增加末梢速度
- 随挥：拍子向对角线下方随挥，不提前停拍

**扣杀（Smash）**
- 起跳时机：在球下落至最佳击球点前起跳（非球到达后才起）
- 击球点：身体前方最高点，不让球过头顶
- 手腕下压：击球瞬间手腕迅速下压，制造向下角度
- 身体旋转：引臂时肩膀旋转拉弓，击球时反向旋转发力
- 落地稳定：以单脚（右手持拍者用右脚）缓冲落地

**网前技术**
- 搓球：拍面稍开，轻搓球底部制造向下旋转
- 推球：平推球头，贴网而过
- 扑球：提前移至网前，拍头超过球网向下扑击

**防守**
- 重心：低重心、膝微弯，随时可移动
- 反拍防守：拇指上移至拍边（拇指发力）
- 到位时机：在球落点前调整好步法

### 步法系统（六点步法）

**六个方向**：前左、前右、中左、中右、后左、后右
- 前场：弓箭步前冲，右手持拍者右脚迈右前
- 后场：蹬跳步，背对网跑动时转肩调整
- T型中心返回：每次击球后立即回到场地中心（底线中间）

**步法节拍**：击球 → 回中心 → 分步等待 → 预判移动

### 问题类型标签表

| 问题类型 | 英文标签 | 说明 |
|---------|---------|------|
| 步法迟缓 | `LATE FOOTWORK` | 未提前到达击球位置 |
| 缺少分步预判 | `NO SPLIT STEP` | 对方击球前未做分步准备 |
| 弓步步法过晚 | `LATE LUNGE` | 前场弓步到位太晚 |
| 回位不及时 | `POOR RECOVERY` | 击球后未及时返回场地中心 |
| 握拍错误 | `WRONG GRIP` | 握拍方式与击球类型不匹配 |
| 手腕未爆发发力 | `NO WRIST SNAP` | 击球时手腕未爆发性旋前/旋后 |
| 缺乏躯干旋转 | `NO ROTATION` | 缺乏躯干旋转，纯手臂挥拍 |
| 随挥不足 | `NO FOLLOW-THRU` | 击球后拍子未完成随挥弧线 |
| 击球点过晚或过低 | `LATE CONTACT` | 接触球时球已落至过低位置 |
| 扣杀角度差 | `BAD SMASH ANG` | 扣杀过平或过陡 |
| 高远球不够深 | `FLAT CLEAR` | 高远球未到达对方后场 |
| 网前推搓球错误 | `HAIRPIN ERROR` | 网前推搓拍面角度或力度错误 |
| 准备姿势不正确 | `WRONG STANCE` | 准备姿势过于僵硬或站位错误 |
| 网前站位不合理 | `WRONG NET POS` | 扑球或推球时网前站位过近/过远 |
| 缺乏假动作欺骗 | `NO DECEPTION` | 出球方向过于明显，无欺骗性 |
| 追球视线过晚 | `POOR TRACKING` | 未从对方击球瞬间开始追球 |
| 应跳扣未起跳 | `NO JUMP SMASH` | 有机会跳扣却从地面扣球 |
| 发球高度不合适 | `BAD SERVE HT` | 发球高度不符合所选发球类型 |
| 技术正确 | `GOOD TECH` | 正面标注，绿色圈 |
| 步法优秀 | `GOOD FOOTWORK` | 正面标注 |
| 假动作出色 | `GOOD DECEPTION` | 正面标注 |

---

## Step 1：综合教练分析（coach.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --output-dir "output/badminton" --context "这是一段羽毛球训练视频。请全程用中文进行专业羽毛球教练分析。综合评估：扣杀技术（手腕发力、击球点、旋转）、步法移动（六点步法、回位）、网前技术。每个问题注明帧号，给出具体修正建议。"
```

输出：`output/badminton/coach_*.md`、`output/badminton/frames/`

---

## Step 2：部位标注（badminton_annotate.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 badminton_annotate.py
```

标注：Body（重心）/ Racket Hand（持拍手）/ Off Hand（非持拍手）/ Lead Foot / Back Foot
输出：`output/badminton/annotated/` + `output/badminton/annotate_*.md`

---

## ⚠️ GPT-4o 调用注意事项
- 英文 system prompt，不提识别人物，用 biomechanics analysis，detail=low
- System prompt 声明："badminton training footage for technique improvement"
