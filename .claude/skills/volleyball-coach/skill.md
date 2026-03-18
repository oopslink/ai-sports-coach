---
name: volleyball-coach
description: 排球视频教练分析 skill。当用户提供排球训练或比赛视频并希望获得技术分析时立即使用。触发词：排球、volleyball、扣球、垫球、传球、发球、拦网、助跑、平台、二传等。
---

# 排球视频教练分析

## 标准分析流程（三步必做）

```
Step 1: coach.py               → 提取帧 + GPT-4o 综合分析 → output/volleyball/coach_*.md
Step 2: volleyball_annotate.py → 标注每帧关键部位          → output/volleyball/annotated/ + output/volleyball/annotate_*.md
Step 3: 向用户输出结构化分析报告
```

用户要求 PPT 时：`node output/volleyball/gen_ppt.js`

---

## 报告内容标准（每次分析必须包含）

### 1. 综合评分（X/10）
维度：扣球技术 / 垫球防守 / 传球二传 / 发球技术 / 拦网 / 移动脚步

### 2. 亮点（✅）— 2-3 个，注明帧号

### 3. 问题逐帧深度分析（❌ 每个问题独立一节）
- **标注图片**：`output/volleyball/annotated/frame_XXX.jpg`
- **帧号 + 问题类型标签**
- **问题描述**：3-5 条
- **正确动作要领**：3-4 条
- **专项训练**：1-2 个（含频次）

### 4. 问题汇总表 | 5. 专项训练计划 | 6. 教练总结

---

## 排球教练分析框架

### 扣球技术（Spike）

**助跑节奏（3步/4步助跑）**
- 标准三步：左→右→左右（右手选手）
- 最后两步制动：右脚先踏地减速，左脚随即跟上并拢
- 起跳：双脚蹬地，手臂由后向前上摆动辅助

**击球动作**
- 引臂：起跳后引臂至耳侧，形成"弓形"蓄力
- 挥臂：以肩为轴，大臂带动小臂向前上方挥出
- 接触点：球在右肩前上方（不让球过头顶后方）
- 手腕压球：击球时手腕快速向下压，制造向下角度和旋转
- 随挥：击球后继续随挥，不突然停臂

### 垫球技术（Dig）

**平台（Platform）**
- 双手叠合（拇指平行朝前），小臂绷紧形成水平平面
- 手臂锁直，关节不弯曲
- 接触点：靠近手腕处（不用手指或手掌根部）

**垫球角度控制**
- 根据来球方向调整平台角度
- 低球：下蹲膝盖吸收力量，再垫球
- 大角度来球：身体侧对来球，平台偏向目标方向

### 传球技术（Set）

**手型**
- 双手置额头前，虎口相对，形成菱形窗口
- 十指张开，用指尖第一关节触球

**传球力量与方向**
- 正传：腰腿蹬伸，双臂向目标推送
- 背传：腰部反弓后挺，手臂向后上方推送
- 跳传：起跳在最高点传球

### 发球技术（Serve）

**飘球（Float Serve）**
- 抛球：离身一臂距离，高度约 30cm，稳定一致
- 击球：手掌根部用力击球正中，手腕不随挥（无旋转）

**上旋发球（Top Spin Serve）**
- 抛球更高（约 50-60cm）
- 击球时手腕快速前压制造强烈上旋

### 问题类型标签表

| 问题类型 | 英文标签 | 说明 |
|---------|---------|------|
| 垫球平台错误 | `WRONG PLATFORM` | 平台角度不水平或双臂未并拢 |
| 垫球角度偏差 | `WRONG DIG ANG` | 垫球角度导致球偏离二传位置 |
| 手臂未锁直 | `PLATFORM UNLOCK` | 垫球时肘关节弯曲，平台不稳 |
| 传球手型错误 | `WRONG SET HANDS` | 手型未形成标准菱形窗口 |
| 举手准备过晚 | `LATE SET HANDS` | 球到达前双手未举到传球位置 |
| 传球落点错误 | `WRONG SET LOC` | 传球距网过近、过远或高度不对 |
| 扣球助跑差 | `POOR APPROACH` | 三/四步助跑节奏或角度错误 |
| 挥臂幅度不足 | `POOR ARM SWING` | 挥臂未充分利用肩部旋转发力 |
| 扣球手腕未压 | `NO WRIST SNAP` | 扣球瞬间手腕未快速下压 |
| 起跳时机错误 | `BAD JUMP TIMING` | 跳跃时机导致在下落阶段击球 |
| 发球抛球差 | `BAD TOSS` | 抛球位置不一致影响发球稳定性 |
| 飘球接触点偏 | `BAD FLOAT HIT` | 飘球未击中球正中，球产生旋转 |
| 拦网时机差 | `BLOCK TIMING` | 起跳过早或过晚导致拦网失败 |
| 拦网手未压网 | `NO PENETRATION` | 拦网双手未越网压扣，角度减少不足 |
| 准备姿势差 | `NOT READY` | 动作前身体未进入运动员准备状态 |
| 重心不稳 | `OFF BALANCE` | 动作中或动作后失去平衡 |
| 接发球到位率差 | `POOR RECEPTION` | 接发球平台方向偏，传不到二传 |
| 未保护扣球 | `NO COVERAGE` | 扣球时队友未在周围形成保护阵型 |
| 技术正确 | `GOOD TECH` | 正面标注，绿色圈 |
| 移动优秀 | `GOOD MOVEMENT` | 正面标注 |
| 传球到位 | `GOOD SET` | 正面标注 |

---

## Step 1：综合教练分析（coach.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 coach.py --video "<视频路径>" --output-dir "output/volleyball" --context "这是一段排球训练视频。请全程用中文进行专业排球教练分析。综合评估：扣球助跑节奏和击球点、垫球平台角度和手臂姿势、传球手型、发球抛球稳定性。每个问题注明帧号，给出具体修正建议。"
```

输出：`output/volleyball/coach_*.md`、`output/volleyball/frames/`

---

## Step 2：部位标注（volleyball_annotate.py）

```bash
cd /Users/oopslink/works/codes/oopslink/ai-sports-coach
python3 volleyball_annotate.py
```

标注：Body（重心）/ Left Arm（左臂）/ Right Arm（右臂）/ Lead Foot / Back Foot
输出：`output/volleyball/annotated/` + `output/volleyball/annotate_*.md`

---

## ⚠️ GPT-4o 调用注意事项
- 英文 system prompt，不提识别人物，用 biomechanics analysis，detail=low
- System prompt 声明："volleyball training footage for technique improvement"
