---
name: football-coach
description: 足球视频教练分析 skill。当用户提供足球训练或比赛视频并希望获得技术分析时立即使用。触发词：足球、football、soccer、射门、传球、控球、过人、跑位、踢球、头球等。
---

# 足球视频教练分析

## 标准分析流程（三步必做）

```
Step 1: coach.py            → 提取帧 + GPT-4o 综合分析 → output/football/coach_*.md
Step 2: football_annotate.py → 标注每帧关键部位         → output/football/annotated/ + output/football/annotate_*.md
Step 3: 向用户输出结构化分析报告
```

用户要求 PPT 时：`node output/football/gen_ppt.js`

---

## 报告内容标准（每次分析必须包含）

### 1. 综合评分（X/10）
维度：射门技术 / 传球精准 / 控球技术 / 跑位意识 / 身体对抗 / 整体流畅度

### 2. 亮点（✅）— 2-3 个，注明帧号

### 3. 问题逐帧深度分析（❌ 每个问题独立一节）
- **标注图片**：`output/football/annotated/frame_XXX.jpg`
- **帧号 + 问题类型标签**
- **问题描述**：3-5 条
- **正确动作要领**：3-4 条
- **专项训练**：1-2 个（含频次）

### 4. 问题汇总表 | 5. 专项训练计划 | 6. 教练总结

---

## 足球教练分析框架

### 射门技术

**脚背射门（Instep Drive）**
- 助跑角度：与球成 30-45° 斜角助跑
- 支撑脚落点：落于球侧方约 15cm，脚尖指向目标
- 踢球部位：脚背正中（趾骨与跖骨交界处）
- 踝关节：击球瞬间踝关节锁紧，不松弛
- 随动：踢球脚自然随动向上，身体微前倾

**内侧传球/射门（Inside Pass）**
- 脚型：内脚背（大脚趾到脚跟的内侧平面）
- 支撑脚：正对目标方向，落在球旁侧
- 接触点：球心偏后，制造平直或低平弹道

**外脚背（Outside Kick）**
- 脚型：小脚趾侧脚背弧面
- 应用：香蕉球、弧线传中

### 控球技术

**停球（First Touch）**
- 停球原则：软接触（柔性缓冲减速球的力量）
- 方式：脚内侧停、脚背停、大腿停、胸停
- 目的：把球停在下一步动作最有利的位置

**带球**
- 触球频率：快速推进时每 1-1.5 步触球一次
- 球与脚距离：保持在一步以内，不远离控制范围

### 跑位与无球动作

- 拉开空间：在防守球员后方做斜线插上
- 背身接球：背对进攻方向时身体对抗技巧
- 换位跑动：与队友形成换位创造空间

### 问题类型标签表

| 问题类型 | 英文标签 | 说明 |
|---------|---------|------|
| 踢球部位错误 | `WRONG CONTACT` | 未用正确脚型（内侧/脚背/外脚背）接触球 |
| 踝关节未锁紧 | `ANKLE UNLOCK` | 踝关节松弛，力量传递损失 |
| 随动不足 | `NO FOLLOW-THRU` | 踢球后腿部未充分随动 |
| 弱脚使用不足 | `WEAK FOOT` | 非优势脚技术明显偏差 |
| 身体后仰 | `BODY LEAN` | 身体后仰导致球飞高偏上 |
| 头部抬起 | `HEAD UP` | 击球瞬间头部抬起，未跟踪球 |
| 重心不稳 | `OFF BALANCE` | 击球前后失去身体平衡 |
| 接球前未肩部观察 | `NO SHLD CHECK` | 接球前未扫视盲区，信息不足 |
| 助跑角度差 | `POOR APPROACH` | 助跑角度影响射门精准度和力量 |
| 站位不佳 | `POOR POS` | 接球/控球时位置不合理 |
| 传球选择错误 | `WRONG PASS` | 选择了错误类型或方向的传球 |
| 跑位时机错误 | `POOR RUN TIMING` | 提前或过晚跑动导致越位或失去空间 |
| 第一脚触球差 | `POOR 1ST TOUCH` | 接球第一触球过重或方向偏 |
| 传球力道不当 | `WRONG WEIGHT` | 传球力度与接球者跑动速度不匹配 |
| 未合理护球 | `NO SHIELDING` | 未用身体挡开防守者保护球 |
| 头球技术差 | `POOR HEADING` | 头球用脑门区域不正确或无爆发力 |
| 传中质量差 | `POOR CROSS` | 传中落点太高/太低/偏后 |
| 逼抢时机过晚 | `LATE PRESS` | 逼抢时间延迟，允许对方转身或前送 |
| 技术正确 | `GOOD TECH` | 正面标注，绿色圈 |
| 移动优秀 | `GOOD MOVE` | 正面标注 |
| 视野意识好 | `GOOD VISION` | 正面标注 |

---

## Step 1：综合教练分析（coach.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --output-dir "output/football" --context "这是一段足球训练视频。请全程用中文进行专业足球教练分析。综合评估：射门技术（脚型、踝关节、随动）、传球精准度、控球第一脚触球、跑位意识。每个问题注明帧号，给出具体修正建议。"
```

输出：`output/football/coach_*.md`、`output/football/frames/`

---

## Step 2：部位标注（football_annotate.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 football_annotate.py
```

标注：Body（重心）/ Kick Foot（踢球脚）/ Stand Foot（支撑脚）/ Head（头部）/ Hip（髋部）
输出：`output/football/annotated/` + `output/football/annotate_*.md`

---

## ⚠️ GPT-4o 调用注意事项
- 英文 system prompt，不提识别人物，用 biomechanics analysis，detail=low
- System prompt 声明："football/soccer training footage for technique improvement"
