# 灵析 AI 智能投顾助手 — 四层架构图

> 版本：v1.4 · 更新日期：2026-06-23  
> 适用场景：面试作品集 / 架构答辩 / 产品评审

---

## 四层架构总览

```mermaid
graph TD
    subgraph L1["交互层 Interaction Layer"]
        direction TB
        P1["首页"]
        P2["持仓导入"]
        P3["持仓诊断"]
        P4["周期分析"]
        P5["情绪纠偏"]
        P6["投教"]
        P7["分析溯源"]
        P8["合规说明"]
        A1["追问助手"]
        A2["投教问答"]
        A3["AI 反馈"]
    end

    subgraph L2["规则风控层 Risk Control Layer"]
        direction TB
        R1["规则引擎<br/>禁止词库 · 数值校验"]
        R2["7 步审计日志"]
        R3["合规拦截记录"]
    end

    subgraph L3["模型层 Model Layer"]
        direction TB
        M1["LSTM v2.0 周期预测<br/>30日×7特征 · RMSE 3.39"]
        M2["随机森林 v2.2 风险评级<br/>14维 · 准确率 61.17%"]
        M3["LLM · DeepSeek<br/>投教问答 · 诊断追问"]
    end

    subgraph L4["数据层 Data Layer"]
        direction TB
        D1["Tushare · AKShare<br/>行情 · 估值 · 情绪"]
        D2["SQLite<br/>审计日志 · 反馈记录"]
        D3["localStorage<br/>AES-256 加密持仓"]
    end

    P1 --> R1
    P2 --> R1
    P3 --> R1
    P3 --> R2
    P4 --> R1
    P5 --> R1
    P6 --> R1
    P7 --> R2
    P8 --> R3
    A1 --> R1
    A1 --> R3
    A2 --> R1
    A3 --> R2

    R1 --> M1
    R1 --> M2
    R1 --> M3
    R2 --> M1
    R2 --> M2
    R3 --> D2

    M1 --> D1
    M2 --> D1
    M3 --> D1

    R2 --> D2
    A3 --> D2

    P2 --> D3
    P3 --> D3
    P5 --> D3

    M1 -.-> D2
    M2 -.-> D2

    style L1 fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    style L2 fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#9a3412
    style L3 fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    style L4 fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#5b21b6

    style P1 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P2 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P3 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P4 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P5 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P6 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P7 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style P8 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style A1 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style A2 fill:#bfdbfe,stroke:#2563eb,color:#1e40af
    style A3 fill:#bfdbfe,stroke:#2563eb,color:#1e40af

    style R1 fill:#fed7aa,stroke:#ea580c,color:#9a3412
    style R2 fill:#fed7aa,stroke:#ea580c,color:#9a3412
    style R3 fill:#fed7aa,stroke:#ea580c,color:#9a3412

    style M1 fill:#bbf7d0,stroke:#16a34a,color:#166534
    style M2 fill:#bbf7d0,stroke:#16a34a,color:#166534
    style M3 fill:#bbf7d0,stroke:#16a34a,color:#166534

    style D1 fill:#ddd6fe,stroke:#7c3aed,color:#5b21b6
    style D2 fill:#ddd6fe,stroke:#7c3aed,color:#5b21b6
    style D3 fill:#ddd6fe,stroke:#7c3aed,color:#5b21b6
```

---

## 层级说明

| 层级 | 颜色 | 职责 | 核心组件 |
| --- | --- | --- | --- |
| **交互层** | 蓝色 | 用户触达与信息呈现 | 8 大功能页 + 追问助手 + 投教问答 + AI 反馈 |
| **规则风控层** | 橙色 | 合规校验、过程留痕、拦截记录 | 规则引擎、7 步审计、合规拦截 |
| **模型层** | 绿色 | 智能分析与知识生成 | LSTM、随机森林、DeepSeek LLM |
| **数据层** | 紫色 | 数据获取、持久化与隐私存储 | Tushare、AKShare、SQLite、localStorage |

---

## 层间调用关系（简述）

```
交互层
  → 规则风控层：所有用户输入与 AI 输出先过规则引擎；诊断链路写入 7 步审计；越界咨询写入合规记录
  → 数据层：持仓读写 localStorage；反馈与审计写入 SQLite

规则风控层
  → 模型层：规则放行后调用 LSTM / 随机森林 / LLM
  → 数据层：审计与合规记录持久化

模型层
  → 数据层：LSTM / RF 读取 Tushare 行情与 AKShare 估值（Tushare 降级）；分析结果回写审计日志

数据层
  → 向上供给：行情与情绪数据、估值分位、历史审计、本地加密持仓
```

---

## 各层组件清单

### 1. 交互层（蓝色）

| 类型 | 组件 |
| --- | --- |
| 功能页面 | 首页、持仓导入、持仓诊断、周期分析、情绪纠偏、投教、分析溯源、合规说明 |
| 嵌入式能力 | 追问助手（诊断页底部）、投教问答（投教页右侧）、AI 反馈（诊断/分析结果页） |

### 2. 规则风控层（橙色）

| 组件 | 说明 |
| --- | --- |
| 规则引擎 | 禁止词库拦截（荐股、承诺收益等）；数值校验（PE 异常、集中度阈值等） |
| 7 步审计日志 | 请求接收 → 数据获取 → 数据清洗 → 模型预测 → 风险评估 → 规则校验 → 结果生成 |
| 合规拦截记录 | 越界咨询拦截留痕，支撑合规面板实时统计 |

### 3. 模型层（绿色）

| 模型 | 输入特征 | 输出 | 生产指标 |
| --- | --- | --- | --- |
| **LSTM v2.0** | 30 日 × 7 维：close · pct_chg · vol · pe_pct · pb_pct · turnover_rate · amplitude | 未来 5 日 PE 趋势参考 | RMSE **3.39**，MAE **2.52** |
| **随机森林 v2.2** | 14 维（11 基线 + 3 交互：PE×波动率等） | 低 / 中 / 高风险三分类 | 准确率 **61.17%**，F1 **61.19%** |
| **LLM（DeepSeek）** | 用户问题 + 合规 Prompt + 上下文（诊断/投教） | 投教解答、诊断追问回复 | — |

### 4. 数据层（紫色）

| 数据源 | 存储 / 接口 | 用途 |
| --- | --- | --- |
| **Tushare Pro** | 外部行情接口 | 实时行情、行业分类、市场情绪 |
| **AKShare** | 估值接口（优先） | PE/PB 分位；Tushare 不可用时降级 |
| **SQLite** | 服务端本地库 | 审计日志、用户反馈记录 |
| **localStorage** | 浏览器本地 | AES-256 加密持仓，默认不上云 |

---

## 简化版架构图（演讲用）

> 仅展示四层纵向关系，适合 1 分钟快速讲解。

```mermaid
graph TD
    L1["交互层<br/>8 页面 · 追问 · 投教 · 反馈"]
    L2["规则风控层<br/>规则引擎 · 7 步审计 · 合规拦截"]
    L3["模型层<br/>LSTM v2.0 · RF v2.2 · DeepSeek LLM"]
    L4["数据层<br/>Tushare · AKShare · SQLite · localStorage"]

    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 -.-> L1

    style L1 fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    style L2 fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#9a3412
    style L3 fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
    style L4 fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#5b21b6
```
