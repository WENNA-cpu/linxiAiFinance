# 灵析 AI 智能投顾助手 — 产品功能清单

> 版本：v1.4 · 更新日期：2026-06-23 · 状态基于 `frontend/` + `backend/` 主代码路径

---

## 核心功能总览

| # | 功能名称 | 路由 / API | 状态 | 说明 |
|---|----------|------------|------|------|
| 1 | **导入持仓** | `/portfolio/import` | ✅ 已完成 | AES-256 本地加密，安全承诺弹窗 |
| 2 | **AI 持仓智能诊断** | `/portfolio/diagnosis`<br/>`POST /api/portfolio/diagnose` | ✅ 已完成 | 7 步审计 + LSTM v2.0 + RF v2.2 + 规则引擎 |
| 3 | **诊断追问助手** | **诊断页底部**<br/>`POST /api/diagnose/chat` | ✅ **v1.3 完整** | RAG 持仓上下文 + 合规拦截 + DeepSeek |
| 4 | **AI 资产周期分析** | `/cycle`<br/>`POST /api/cycle/analyze` | ✅ 已完成 | PE/PB 分位 + ECharts LSTM v2.0 预测虚线 |
| 5 | **AI 投资情绪纠偏** | `/emotion` | ✅ **真实持仓驱动** | 确认偏误 / 损失厌恶 / 羊群效应 / 行为矫正 |
| 6 | **投教聊天问答** | **投教页右侧**<br/>`POST /api/education/chat` | ✅ **v1.3 完整** | DeepSeek 理财知识问答 + 合规 prompt |
| 7 | **场景化投教课程** | `/education` | ✅ 已完成 | 静态课程库 + 课程详情页 |
| 8 | **AI 分析依据溯源** | `/trace/:requestId` | ✅ 已完成 | 7 步审计日志 + ECharts DAG |
| 9 | **风控规则兜底** | `/compliance` | ✅ 已完成 | 禁止词拦截 + 基于系统运行日志的实时统计 |
| 10 | **模型版本回滚** | `POST /api/admin/model/rollback` | ✅ **v1.3 新增** | HTTP 管理 + 热重载，无需重启 |

---

## v1.4 重点更新

| 能力 | v1.3 | v1.4 当前 |
| ---- | ---- | --------- |
| LSTM | 五特征 RMSE 14.56 | **v2.0 七特征 RMSE 3.39**（+换手率、振幅） |
| 随机森林 | 基线 ~57% | **v2.2 61.17%**（14 维 + 交互特征 + 超参调优） |
| 估值数据源 | Tushare 单源 | **AKShare 优先、Tushare 降级** |
| 部署 | 秒悟 | **Docker Compose + ECS Nginx**（`DEPLOY.md`） |
| 诊断追问 / 投教 / 回滚 | 已上线 | 保持，文档与 PRD §6.11 对齐 |

---

## v1.3 历史更新（保留）

| 能力 | v1.2 | v1.3 |
| ---- | ---- | ---- |
| 诊断追问助手 | 基础 DeepSeek | RAG 持仓上下文 · 持仓内/外分流 · 合规前置 |
| 投教聊天 | 课程为主 | 右侧 EducationChatPanel · DeepSeek 即时问答 |
| 模型回滚 | 仅库函数 | HTTP API + 版本别名 + 热重载 |
| 情绪纠偏 | 真实持仓 | 行为矫正估算 · 风险系数动态计算 |

---

## 功能详细说明

### 1. 导入持仓 ✅

| 项 | 内容 |
|----|------|
| 前端 | `PortfolioImport.vue` |
| 加密 | `portfolioCrypto.ts` — AES-256，格式 `enc:v1:{ciphertext}` |
| 行为 | 导入后自动 `refresh-quotes` 拉取 Tushare 最新收盘 |

### 2. AI 持仓智能诊断 ✅

| 项 | 内容 |
|----|------|
| 前端 | `PortfolioDiagnosis.vue` + 「刷新现价」 |
| 后端 | `portfolio.py` — 7 步 `record_audit_step` |
| 模型 | LSTM v2.0（灰度 5%）+ RF v2.2 + 规则兜底 |
| 数据源 | Tushare 实时行情；估值 AKShare 优先；异常时历史缓存动态更新 |

**7 步审计：**

1. 请求接收  
2. 数据获取  
3. 数据清洗  
4. LSTM v2.0 模型预测  
5. 随机森林 v2.2 风险评估  
6. 规则引擎校验  
7. 结果生成  

**随机森林 v2.2 特征（14 维）：**

- 基线 11 维：波动率、换手率、PE/PB 分位、RSI、MA 乖离、布林带宽度、量比等  
- 交互 3 维：PE×波动率、PB×波动率、PE×换手率  
- 服务：`rf_risk_service.py` · 模型 `rf_risk.pkl` · 准确率 **61.17%**

### 3. 诊断追问助手 ✅（v1.3 重点）

| 项 | 内容 |
|----|------|
| **位置** | 持仓诊断结果页 **底部**（`PortfolioDiagnosis.vue`） |
| **API** | `POST /api/diagnose/chat`（`diagnose_chat.py`） |
| **RAG 上下文** | 注入本次诊断 `diagnosis_context`：资产列表、风险等级、涨跌幅、成本、现价 |
| **合规拦截** | `rule_engine.check_question()` 前置；11 禁止词 → 403，零 LLM 调用 |
| **DeepSeek** | 规则放行后 `chat_completion()`，model=`deepseek-chat` |
| **持仓内股票** | **portfolio 模式**：匹配持仓资产，回答含成本价、现价、盈亏、风险等级 |
| **持仓外股票** | **external 模式**：Tushare `stock_basic` 识别，通用介绍，禁止买卖建议 |
| **整体持仓** | **general 模式**：基于诊断摘要回答 |

**典型验证场景：**

| 输入 | 预期 |
| ---- | ---- |
| 「茅台现在能买吗」 | 403 拦截（禁止词「能买吗」） |
| 「我的持仓风险集中吗」 | 200，基于诊断上下文回答 |
| 「宁德时代怎么样」（不在持仓） | 200，external 模式通用介绍 |

### 4. AI 资产周期分析 ✅（LSTM v2.0）

| 项 | 内容 |
|----|------|
| 前端 | `AssetCycle.vue` — PE 主图 + **橙色 LSTM 预测虚线（5 日）** |
| 后端 | `cycle.py` + `lstm_cycle_service.py` |
| 输入特征 | `close` · `pct_chg` · `vol` · `pe_pct` · `pb_pct` · `turnover_rate` · `amplitude` |
| 模型 | `lstm_cycle.h5`（= `lstm_v2.0.h5`）+ Scaler |
| 评估 | RMSE **3.39**，MAE **2.52**（HS300 300 股 × 3 年） |
| 估值 | AKShare 优先获取 PE/PB，Tushare 降级 |
| 灰度 | `NEW_MODEL_RATIO=5%` |

### 5. AI 投资情绪纠偏 ✅（v1.3 重点）

| 项 | 内容 |
|----|------|
| 前端 | `EmotionCorrection.vue` |
| 后端 | `market.py` — sentiment / behavior-bias / emotion-portfolio-context |

**行为偏差指标：**

| 指标 | 计算方式 | 展示 |
| ---- | -------- | ---- |
| **确认偏误** | 最高行业 **市值占比** | 百分比 + 行业名；≥50% 高亮 |
| **损失厌恶** | **亏损资产数量** | 只数 + 资产盈亏状态列表 |
| **羊群效应** | 行业集中度 | 最高行业 >50% →「较高」；≥3 行业 →「较低」 |
| **过度自信** | 持仓数量 | <5 低 / >10 高 |
| **行为矫正估算** | `portfolioRiskCoef` 动态计算 | 基于真实持仓的动态估算：潜在损失、减少交易次数、改善收益 % |

| 项 | 内容 |
|----|------|
| 情绪指数 | 基于 Tushare 舆情数据实时计算 |
| 行为偏差 | 基于真实持仓与 Tushare 行业分类动态计算 |
| 现价 | `POST /api/portfolio/refresh-quotes` + 页内「刷新现价」 |

### 6. 投教聊天问答 ✅（v1.3 重点）

| 项 | 内容 |
|----|------|
| **位置** | 投教页（`Education.vue`）**右侧** `EducationChatPanel.vue` |
| **API** | `POST /api/education/chat`（`education.py`） |
| **LLM** | DeepSeek `answer_education_question()` |
| **合规** | `EDUCATION_SYSTEM_PROMPT`：禁止买卖建议，200~400 字，带免责声明 |
| **历史** | 保留最近 6 轮对话 |
| **课程** | 左侧静态课程（`courses_full.json`），与聊天独立 |

### 7. 模型版本管理与回滚 ✅（v1.3 重点）

| 项 | 内容 |
|----|------|
| 版本管理 | `model_manager.py` + `models/model_metadata.json` |
| 训练注册 | `register_model_version()` → `models/versions/{type}/{version}/` |
| 查询版本 | `GET /api/admin/model/versions?model_type=lstm` |
| 回滚接口 | `POST /api/admin/model/rollback` |
| 请求体 | `{ "model_type": "lstm" \| "rf", "target_version": "v2.0" \| "v2.2" }` |
| 热重载 | `reload_lstm_predictors()` / `reload_rf_predictor()` — **不重启服务** |
| 运行时配置 | `models/model_runtime.json` 持久化当前版本 |

### 8. AI 分析依据溯源 ✅

| 项 | 内容 |
|----|------|
| 前端 | `Traceability.vue` + `DataLineageChart.vue` |
| 后端 | `trace.py` — `is_complete: len(logs) >= 7` |
| 可视化 | 数据源 → 处理 → 模型 → 输出 DAG |

### 9. 风控规则 + 合规拦截 ✅

| 项 | 内容 |
|----|------|
| 前端 | `Compliance.vue` + 诊断页追问助手 |
| 后端 | `rule_engine.py` + `diagnose_chat.py` |
| 规则 | 11 禁止词；命中 → 403 + `compliance_logs` |
| 统计 | `GET /api/admin/compliance-stats` — 基于系统运行日志的实时统计 |

---

## 辅助功能

| 功能 | 状态 |
|------|------|
| 首页市场情绪简报 | ✅ Tushare 舆情数据实时计算 |
| 商业价值计算器 | ✅ 基于业务模型的动态估算 |
| 现价手动刷新（诊断/纠偏页） | ✅ |
| 灰度发布 NEW_MODEL_RATIO=5 | ✅ |
| Docker / ECS 部署 | ✅ `docker-compose.yml` + `deploy/nginx-ecs.conf` |

---

## 状态图例

| 标记 | 含义 |
|------|------|
| ✅ 已完成 | 前后端联通，核心链路可用 |
| 🔄 待优化 | 功能可用但存在已知缺口 |
| 📋 规划中 | 尚未开发 |

---

## 工程演进项

| 项 | 说明 |
| -- | ---- |
| `feedback.py` 路由 | 部分反馈 API 未挂载到 `main.py` |
| 商业价值计算器 | 首页指标基于业务模型动态估算，持续迭代中 |
| `/api/risk/rating` | 部分端点基于历史数据缓存返回 |

> 核心链路（诊断 → 审计 → 溯源 → 合规 → 追问 → 模型回滚）已全通。
