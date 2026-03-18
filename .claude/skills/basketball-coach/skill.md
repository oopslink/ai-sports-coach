---
name: basketball-coach
description: 篮球视频教练分析 skill。当用户提供篮球训练或比赛视频并希望获得技术分析时立即使用。触发词：篮球、basketball、投篮、运球、防守、步法、肘部、BEEF、跳投、上篮等。
---

# 篮球视频教练分析

## 标准分析流程（三步必做）

```
Step 1: coach.py               → 提取帧 + GPT-4o 综合分析 → output/basketball/coach_*.md
Step 2: basketball_annotate.py → 标注每帧关键部位          → output/basketball/annotated/ + output/basketball/annotate_*.md
Step 3: 向用户输出结构化分析报告
```

用户要求 PPT 时：`node output/basketball/gen_ppt.js`

---

## 报告内容标准（每次分析必须包含）

### 1. 综合评分（X/10）
维度：投篮技术 / 控球能力 / 防守站位 / 篮板争抢 / 移动脚步 / 整体流畅度

### 2. 亮点（✅）— 2-3 个，注明帧号

### 3. 问题逐帧深度分析（❌ 每个问题独立一节）
- **标注图片**：`output/basketball/annotated/frame_XXX.jpg`
- **帧号 + 问题类型标签**
- **问题描述**：3-5 条
- **正确动作要领**：3-4 条
- **专项训练**：1-2 个（含频次）

### 4. 问题汇总表 | 5. 专项训练计划 | 6. 教练总结

---

## 篮球教练分析框架

### 投篮技术（BEEF 原则）

**Balance（平衡）**
- 双脚与肩同宽或略宽，脚尖朝向篮筐
- 膝盖微弯，重心稍低，接球后立即调整脚步

**Eyes（眼睛）**
- 固定看篮筐前沿（高弧线时看后沿）
- 出手前全程不低头看球，也不看防守人

**Elbow（肘部）**
- 投篮肘对准篮筐方向，不向外翻
- 肘在球正下方，形成"L"形托球

**Follow Through（随挥）**
- 出手后手腕下折（"鹅颈"动作）
- 手指向篮筐延伸，保持姿势直到球入网
- 投篮弧度目标：45-55° 抛物线角度

### 控球技术

**运球基础**
- 手指控球（不用手掌），手腕柔性推送
- 运球高度：腰部以下（防守时膝盖高度）
- 眼睛看前方，禁止低头看球
- 非运球手主动保护球

**变向运球**
- 胯下运球：两腿稍宽，球在两腿间快速交换
- 背后运球：身体向运球方向轻微前倾
- 转身运球：以内侧脚为轴心完成旋转

### 防守技术

**防守步法（Defensive Slide）**
- 低重心：膝盖弯曲，臀部下沉
- 禁止交叉步横移（交叉容易被过掉）
- 手部：一手干扰传球线，一手防运球方向

**盖帽时机**
- 在球的最高点时起跳（非随进攻者跳）
- 方向向上盖，不向前扑（犯规风险）

### 问题类型标签表

| 问题类型 | 英文标签 | 说明 |
|---------|---------|------|
| 出手弧度过平 | `FLAT ARC` | 投篮抛物线太平，低于45°，命中率低 |
| 肘部外翻 | `ELBOW FLARE` | 投篮时肘部向外偏离篮筐方向 |
| 手腕未随挥 | `NO WRIST FLIP` | 出手后手腕无下折，球无后旋 |
| 出手点过低 | `LATE RELEASE` | 球在头部以下位置出手，易被封盖 |
| 出手不稳 | `OFF BALANCE` | 投篮时重心不稳或身体倾斜 |
| 膝盖未弯曲蓄力 | `NO LEG BEND` | 接球后未充分弯曲膝盖积蓄力量 |
| 持球低头 | `BALL WATCHING` | 运球时低头看球，失去场上视野 |
| 控球不稳 | `POOR HANDLE` | 运球节奏或力度控制差 |
| 过度运球 | `OVER DRIBBLE` | 明可传球却反复运球消耗时机 |
| 弱手保护不足 | `WEAK HAND` | 非运球手未护球，易被断 |
| 步法不到位 | `POOR FOOTWORK` | 起跳前步法未调整好 |
| 转身步法错误 | `WRONG PIVOT` | 转身轴心脚抬起（走步）或效率差 |
| 补防关闭过晚 | `LATE CLOSEOUT` | 快速补防时速度不足，给对手空位 |
| 防守站位差 | `POOR DEF STANCE` | 防守时站位过直，重心过高 |
| 未卡位抢篮板 | `NO BOX OUT` | 未在对手前方建立卡位争抢篮板 |
| 未做到断球位防守 | `NO BALL DENIAL` | 未封堵一次传球距离内的接球线 |
| 突破角度差 | `POOR DRIVE ANG` | 向防守帮扶方向突破，利用率低 |
| 未用假动作 | `NO SHOT FAKE` | 错过用假动作造成犯规或空位的机会 |
| 技术正确 | `GOOD FORM` | 正面标注，绿色圈 |
| 移动优秀 | `GOOD MOVEMENT` | 正面标注 |
| 防守积极 | `GOOD DEFENSE` | 正面标注 |

---

## Step 1：综合教练分析（coach.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --output-dir "output/basketball" --context "这是一段篮球训练视频。请全程用中文进行专业篮球教练分析。综合评估：投篮技术（BEEF原则：平衡、眼睛、肘部、随挥）、运球控球、防守站位、步法移动。每个问题注明帧号，给出具体修正建议。"
```

输出：`output/basketball/coach_*.md`、`output/basketball/frames/`

---

## Step 2：部位标注（basketball_annotate.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 basketball_annotate.py
```

标注：Body（重心）/ Shoot Hand（投篮手）/ Guide Hand（辅助手）/ Lead Foot / Back Foot
输出：`output/basketball/annotated/` + `output/basketball/annotate_*.md`

---

## ⚠️ GPT-4o 调用注意事项
- 英文 system prompt，不提识别人物，用 biomechanics analysis，detail=low
- System prompt 声明："basketball training footage for technique improvement"
