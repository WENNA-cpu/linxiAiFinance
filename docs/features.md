# 灵析 AI 智能投顾助手 — 产品功能清单

> 更新日期：2026-06 · 状态基于 `frontend/` + `backend/` 主代码路径

---

## 核心功能总览

| # | 功能名称 | 路由 / API | 状态 | 说明 |
|---|----------|------------|------|------|
| 1 | **导入持仓** | `/portfolio/import` | ✅ 已完成 | AES-256 本地加密存储，安全承诺弹窗，支持清除数据 |
| 2 | **AI 持仓智能诊断** | `/portfolio/diagnosis`<br/>`POST /api/portfolio/diagnose` | ✅ 已完成 | 7 步审计流水线，LSTM + RF + 规则引擎，快速路径 < 1s |
| 3 | **AI 资产周期择时辅助** | `/cycle`<br/>`POST /api/cycle/analyze` | ✅ 已完成 | PE/PB 历史分位 + LSTM 5 日预测，灰度路由 |
| 4 | **AI 投资情绪纠偏** | `/emotion`<br/>`GET /api/market/sentiment` | ✅ 已完成 | 实时情绪指数、行为偏差分析、矫正估算 |
| 5 | **场景化 AI 投教系统** | `/education`<br/>`POST /api/education/chat` | ✅ 已完成 | 课程推荐 + DeepSeek AI 问答，合规 prompt 约束 |
| 6 | **AI 分析依据溯源** | `/trace/:requestId`<br/>`GET /api/trace/{id}` | ✅ 已完成 | 7 步审计日志 + ECharts DAG 血缘图 |
| 7 | **风控规则兜底展示** | `/compliance`<br/>`GET /api/admin/compliance-stats` | ✅ 已完成 | 三层风控说明 + 合规统计动态拉取 |
| 8 | **诊断合规追问** | 诊断页内嵌<br/>`POST /api/diagnose/chat` | ✅ 已完成 | 规则引擎前置拦截 + DeepSeek 合规回答 |

---

## 功能详细说明

### 1. 导入持仓

| 项 | 内容 |
|----|------|
| **前端** | `PortfolioImport.vue` |
| **存储** | `stores/portfolio.ts` + `utils/portfolioCrypto.ts` |
| **加密** | CryptoJS AES-256，密钥 SHA256 派生，格式 `enc:v1:{ciphertext}` |
| **亮点** | 旧版明文自动迁移加密；一键清除本地数据 |
| **待优化** | — |

### 2. AI 持仓智能诊断

| 项 | 内容 |
|----|------|
| **前端** | `PortfolioDiagnosis.vue` |
| **后端** | `api/portfolio.py` |
| **模型** | LSTM 趋势 + RF 风险评级 + 规则引擎兜底 |
| **输出** | 风险资产 / 机会资产 / 置信度 / 节省时间 |
| **缓存** | localStorage `diagnosis_{request_id}` |
| **待优化** | 用户反馈 API（`feedback.py` 未挂载到 main.py） |

### 3. AI 资产周期择时辅助

| 项 | 内容 |
|----|------|
| **前端** | `AssetCycle.vue` |
| **后端** | `api/cycle.py` + `lstm_cycle_service.py` |
| **模型** | LSTM（30 日窗口 → 5 日预测），PE/PB 分位判定 |
| **灰度** | `model_variant: new/legacy`，`NEW_MODEL_RATIO=5%` |
| **待优化** | 模型回滚无 HTTP 管理 API |

### 4. AI 投资情绪纠偏

| 项 | 内容 |
|----|------|
| **前端** | `EmotionCorrection.vue` |
| **后端** | `api/market.py`（sentiment + behavior-bias） |
| **数据源** | Tushare 涨跌停比、成交量等 |
| **输出** | 情绪指数、市场状态、行为偏差、矫正估算 |
| **待优化** | 矫正估算为前端公式演示，非真实回测 |

### 5. 场景化 AI 投教系统

| 项 | 内容 |
|----|------|
| **前端** | `Education.vue` + `EducationChatPanel.vue` |
| **后端** | `api/education.py` + `deepseek_service.py` |
| **LLM** | DeepSeek Chat API |
| **数据** | `data/courses_full.json` + `knowledge_base.json` |
| **待优化** | 课程内容为静态 JSON，未接 CMS |

### 6. AI 分析依据溯源

| 项 | 内容 |
|----|------|
| **前端** | `Traceability.vue` + `DataLineageChart.vue` |
| **后端** | `api/trace.py` + `trace_service.py` |
| **可视化** | ECharts DAG（数据源 → 处理 → 模型 → 输出） |
| **完整性** | `is_complete: len(logs) >= 7` |
| **待优化** | — |

### 7. 风控规则兜底展示

| 项 | 内容 |
|----|------|
| **前端** | `Compliance.vue` |
| **后端** | `api/admin.py` + `compliance_log_service.py` |
| **规则** | `rule_engine.py` 禁止词库（11 词） |
| **统计** | 拦截次数、幻觉修正率、数据泄露事件、规则通过率 |
| **待优化** | 首页部分统计为静态默认值，合规页为动态 API |

### 8. 诊断合规追问

| 项 | 内容 |
|----|------|
| **前端** | `PortfolioDiagnosis.vue` 内嵌聊天 |
| **后端** | `api/diagnose_chat.py` |
| **流程** | 规则引擎前置 → DeepSeek 回答（带诊断上下文） |
| **拦截** | 命中禁止词 → 403 + `compliance_logs` 写入 |
| **待优化** | — |

---

## 辅助功能

| 功能 | 位置 | 状态 |
|------|------|------|
| 首页市场情绪简报 | `Home.vue` + `/api/market/sentiment` | ✅ 已完成 |
| 商业价值计算器 | `Home.vue` 弹窗 | ✅ 已完成（演示数据） |
| 课程详情页 | `CourseDetail.vue` | ✅ 已完成 |
| 管理分析看板 | `GET /api/admin/analytics` | ✅ 已完成 |
| Docker 一键部署 | `docker-compose.yml` + `DEPLOY.md` | ✅ 已完成 |
| 秒悟云部署 | `.env.cloud` + DEPLOY.md §11 | ✅ 已完成 |

---

## 状态图例

| 标记 | 含义 |
|------|------|
| ✅ 已完成 | 前后端联通，核心链路可用 |
| 🔄 待优化 | 功能可用但存在已知缺口 |
| 📋 规划中 | 尚未开发 |
