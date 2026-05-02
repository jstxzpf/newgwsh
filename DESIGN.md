---
name: NewGWSH - 泰兴调查队公文系统
description: 以“权威长卷”为核心，融合政务严谨性与现代高效体验的视觉系统。
colors:
  primary: "#003366"
  neutral-bg: "#f0f2f5"
  paper-white: "#ffffff"
  text-main: "#333333"
  sider-dark: "#003366"
  sider-selected: "#002244"
typography:
  display:
    fontFamily: "方正仿宋_GBK, FZFS, 仿宋, serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.2
  body:
    fontFamily: "方正仿宋_GBK, FZFS, 仿宋, serif"
    fontSize: "16px"
    lineHeight: 1.5
  document:
    fontFamily: "方正仿宋_GBK, FZFS, 仿宋, serif"
    fontSize: "16pt"
    lineHeight: "28pt"
rounded:
  sm: "2px"
  md: "4px"
spacing:
  xs: "8px"
  sm: "16px"
  md: "24px"
  lg: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.sm}"
    padding: "4px 15px"
  card-paper:
    backgroundColor: "{colors.paper-white}"
    rounded: "0px"
    padding: "72px 90px"
---

# Design System: NewGWSH

## 1. Overview

**Creative North Star: "权威长卷 (The Sovereign Scroll)"**

本系统视觉架构的核心逻辑在于将政务公文的“权威性”与现代 Web 的“流动性”有机结合。界面以“长卷”为隐喻，通过大面积的留白和精准的几何分割，营造出一种如同翻开正式档案般的庄重感。

系统拒绝任何浮夸的装饰性元素，强调“设计服务于文字”。每一处间距、每一种对比都经过严密计算，旨在降低长时间公文处理过程中的认知负荷，让用户在“调查队权威蓝”的包围下，感受到极致的专业与沉谨。

**Key Characteristics:**
- **仪式感**: 模拟 A4 纸张的实体感与页边距。
- **秩序美**: 基于 8px 步进的严密间距体系。
- **排版至上**: 仿宋字体栈的绝对主导地位。

## 2. Colors

色彩方案追求深沉的对比与纯净的质感。

### Primary
- **调查队权威蓝** (#003366): 代表系统的核心身份与政务权威。用于侧边栏背景、主按钮及关键状态指示。

### Neutral
- **珍珠白** (#fcfcfc): 用于模拟高品质纸张的质感。
- **空间灰** (#f0f2f5): 作为应用底色，为内容层提供深度的空间感。
- **墨黑** (#333333): 核心文字色，确保在浅色背景上的高清晰度。

### Named Rules
**克制性用色原则**：除了状态警告，全站非中性色占比应严格控制在 10% 以内。权威感来源于灰阶的细腻层次，而非色彩的堆砌。

## 3. Typography

字体是公文系统的灵魂。我们选用了国内政务标准中的“仿宋”字体栈作为全站视觉锚点。

**Display Font:** 方正仿宋_GBK
**Body Font:** 仿宋 (FangSong)

### Hierarchy
- **Display** (600, 32px, 1.2): 用于大标题，传达自信与力量。
- **Headline** (500, 24px, 1.4): 用于模块标题。
- **Document Body** (400, 16pt, 28pt): 核心公文正文，严格遵循 28 磅行距。
- **Label** (400, 14px, 1.2): 用于元数据与表单标签。

### Named Rules
**国标排版原则**：公文编辑区必须确保字号、行距与 GB/T 9704-2023 高度一致，严禁任何形式的字体压缩或拉伸。

## 4. Elevation

系统采用“实体分层”而非“光影叠加”的设计策略。

### Shadow Vocabulary
- **Paper Depth** (0 4px 12px rgba(0,0,0,0.1)): 仅用于赋予 A4 纸张在背景上的实体感。
- **Interactive Glow**: 交互元素（如悬浮按钮）仅使用轻微的色彩加深，不使用投影。

### Named Rules
**扁平优先原则**：除了核心内容载体（纸张），其他界面元素一律保持扁平。深度感通过背景色的微差（fcfcfc vs f0f2f5）来实现。

## 5. Components

组件设计追求“精准而从容”。

### Buttons
- **Shape**: 锐利圆角 (2px)
- **Primary**: 使用调查队权威蓝背景，文字白色，传达决策的果断。

### A4 Paper Engine
- **Style**: 严格的 210mm x 297mm 比例模拟。
- **Padding**: 内边距 (72px 90px) 用于模拟标准公文页边距。

### Navigation
- **Sider**: 采用深蓝底色，未选中项保持极低对比度，确保用户焦点留在内容区。

## 6. Do's and Don'ts

### Do:
- **Do** 使用 OKLCH 进行色彩细微调整以保持感官一致性。
- **Do** 在公文内容区使用 16pt / 28pt 的固定排版比例。
- **Do** 保持 40px 以上的大面积外部留白，突出核心长卷。

### Don't:
- **Don't** 使用纯黑色 (#000) 进行排版。
- **Don't** 在产品模式下使用过度圆润的圆角（如 > 8px）。
- **Don't** 引入任何毛玻璃 (Glassmorphism) 或渐变色效果，这会破坏系统的严谨性。
