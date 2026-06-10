# 灵析 AI 智能投顾助手 — 技术架构文档

> 适用场景：面试作品集 / 技术评审 / 架构答辩

---

## 1. 四层架构总览

```mermaid
flowchart TB
    subgraph L1["第一层 · 交互层 Presentation"]
        UI["Vue 3 + Vite + TailwindCSS"]
        Pages["7 大功能页面"]
        RiskUI["风险提示 · 免责声明 · 安全承诺"]
    end

    subgraph L2["第二层 · 服务层 Service"]
        API["FastAPI REST API"]
        Rule["规则引擎 rule_engine.py"]
        Audit["审计日志 audit_logs"]
        Trace["溯源服务 trace_service.py"]
        Admin["合规统计 admin.py"]
    end

    subgraph L3["第三层 · 模型层 Model"]
        LSTM["LSTM 周期预测<br/>lstm_cycle.h5"]
        RF["随机森林风险评级<br/>rf_risk.pkl"]
        LLM["DeepSeek 投教/追问<br/>deepseek_service.py"]
        Gray["灰度路由 model_manager<br/>NEW_MODEL_RATIO=5%"]
    end

    subgraph L4["第四层 · 数据层 Data"]
        Tushare["Tushare 行情 API"]
        SQLite["SQLite 审计库 lingxi.db"]
        Local["localStorage AES 加密持仓"]
        KB["知识库 JSON / 课程数据"]
    end

    UI --> API
    Pages --> API
    API --> Rule
    API --> Audit
    API --> Trace
    API --> LSTM
    API --> RF
    API --> LLM
    LSTM --> Gray
    RF --> Gray
    API --> Tushare
    Audit --> SQLite
    Trace --> SQLite
    UI --> Local
    LLM --> KB
    LSTM --> Tushare
```

---

## 2. 技术栈说明

### 2.1 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.4 | Composition API + `<script setup>` |
| Vite | 5.x | 构建工具，dev 端口 3015 |
| TypeScript | 5.x | 类型安全 |
| TailwindCSS | 3.x | 原子化样式 |
| Pinia | 2.x | 状态管理（持仓 store） |
| Vue Router | 4.x | Hash 路由 |
| ECharts | 5.x | 溯源血缘 DAG 图 |
| crypto-js | 4.x | AES-256 持仓加密 |

**目录结构：**

```
frontend/src/
├── views/          # 页面（Home, PortfolioDiagnosis, AssetCycle…）
├── components/     # 通用组件（DataLineageChart, RiskBanner…）
├── stores/         # Pinia（portfolio.ts）
├── utils/          # 加密工具（portfolioCrypto.ts）
└── router/         # 路由配置
```

### 2.2 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.104 | REST API 框架 |
| Uvicorn | 0.24 | ASGI 服务器 |
| SQLAlchemy | 2.0 | ORM + SQLite |
| Pandas / NumPy | — | 数据处理 |
| TensorFlow | 2.16 | LSTM 推理 |
| Scikit-learn | 1.3 | 随机森林推理 |
| python-dotenv | — | 环境变量加载 |

**目录结构：**

```
backend/app/
├── api/            # 路由（portfolio, cycle, market, trace, rule…）
├── services/       # 业务逻辑（rule_engine, trace_service, deepseek…）
├── models/         # SQLAlchemy 模型（AuditLog, ComplianceLog）
└── core/           # env_loader 等基础设施

backend/models/     # ML 模型文件 + llm_client
backend/training/   # 训练脚本（train_lstm, train_rf, evaluate_*）
```

### 2.3 部署

| 方式 | 文件 | 说明 |
|------|------|------|
| Docker Compose | `docker-compose.yml` | frontend:80 + backend:8000 |
| 秒悟云平台 | `.env.cloud` | 平台托管，无需 Docker |
| ECS 自建 | `DEPLOY.md` | 阿里云 + Docker 完整指南 |

---

## 3. 核心 API 架构

```mermaid
flowchart LR
    Client["浏览器 / 前端"]

    Client -->|"/api/portfolio/diagnose"| P["portfolio.py"]
    Client -->|"/api/cycle/analyze"| C["cycle.py"]
    Client -->|"/api/market/sentiment"| M["market.py"]
    Client -->|"/api/education/chat"| E["education.py"]
    Client -->|"/api/trace/{id}"| T["trace.py"]
    Client -->|"/api/rule/check"| R["rule.py"]
    Client -->|"/api/diagnose/chat"| D["diagnose_chat.py"]
    Client -->|"/api/admin/compliance-stats"| A["admin.py"]

    P --> LSTM_S["lstm_cycle_service"]
    P --> RF_S["rf_risk_service"]
    P --> RE["rule_engine"]
    P --> AL["audit_logs"]

    C --> LSTM_S
    C --> MM["model_manager 灰度"]

    D --> RE
    D --> DS["deepseek_service"]

    E --> DS

    T --> TS["trace_service"]
    TS --> AL

    A --> CL["compliance_logs"]
```

---

## 4. 数据流图：用户操作 → 审计日志完整链路

以**持仓诊断**为核心链路：

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as 前端 Vue
    participant LS as localStorage<br/>(AES加密)
    participant API as FastAPI<br/>portfolio.py
    participant DS as data_service<br/>(Tushare)
    participant LSTM as LSTM 预测器
    participant RF as 随机森林
    participant RE as 规则引擎
    participant DB as SQLite<br/>audit_logs
    participant Trace as 溯源页

    User->>FE: 导入持仓（代码/成本/数量）
    FE->>LS: AES-256 加密写入
    User->>FE: 点击「开始诊断」
    FE->>API: POST /api/portfolio/diagnose

    Note over API: Step 1: 请求接收
    API->>DB: record_audit_step("请求接收")

    Note over API: Step 2: 数据获取
    alt 用户已提供本地价格
        API->>API: 使用本地价格（快速路径）
    else 需拉取行情
        API->>DS: Tushare daily / daily_basic
        DS-->>API: 行情数据
    end
    API->>DB: record_audit_step("数据获取")

    Note over API: Step 3: 数据清洗
    API->>API: 异常值拦截（涨跌幅>20%）
    API->>DB: record_audit_step("数据清洗")

    Note over API: Step 4: LSTM 预测
    API->>LSTM: 30日窗口 → 5日趋势
    LSTM-->>API: trend_signal
    API->>DB: record_audit_step("LSTM模型预测")

    Note over API: Step 5: RF 风险评估
    API->>RF: volatility, PE分位等特征
    RF-->>API: 低/中/高风险
    API->>DB: record_audit_step("随机森林风险评估")

    Note over API: Step 6: 规则引擎
    API->>RE: 输出内容校验
    RE-->>API: pass / block
    API->>DB: record_audit_step("规则引擎校验")

    Note over API: Step 7: 结果生成
    API->>DB: record_audit_step("结果生成")
    API-->>FE: diagnosis + request_id

    FE->>LS: 缓存 diagnosis_{request_id}
    User->>Trace: 点击「分析溯源」
    Trace->>API: GET /api/trace/{request_id}
    API->>DB: 查询 audit_logs
    API-->>Trace: 7步日志 + lineage DAG
```

### 4.1 合规追问链路

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as 诊断页聊天
    participant API as diagnose_chat.py
    participant RE as 规则引擎
    participant CL as compliance_logs
    participant DS as DeepSeek API

    User->>FE: 输入追问「茅台现在能买吗」
    FE->>API: POST /api/diagnose/chat
    API->>RE: check_question()
    RE-->>API: blocked（命中「能买吗」）
    API->>CL: 写入合规拦截日志
    API-->>FE: 403 + 拦截原因
    FE->>User: 展示合规提示

    User->>FE: 输入「我的持仓风险集中吗」
    FE->>API: POST /api/diagnose/chat
    API->>RE: check_question() → pass
    API->>DS: DeepSeek Chat（带诊断上下文）
    DS-->>API: 合规约束下的回答
    API-->>FE: 200 + 回答内容
```

---

## 5. 模型灰度架构

```mermaid
flowchart TD
    Req["诊断/周期请求"] --> Seed{"灰度 seed<br/>request_id / ts_code"}
    Seed --> Hash["hash('lingxi:' + seed) % 100"]
    Hash --> Compare{"< NEW_MODEL_RATIO ?"}
    Compare -->|是 ~5%| New["新模型<br/>lstm_cycle.h5 / rf_risk.pkl"]
    Compare -->|否 ~95%| Legacy["旧模型<br/>lstm_model.h5 / 规则回退"]
    New --> Meta["model_metadata.json<br/>版本归档"]
    Legacy --> Meta
    Meta --> Resp["响应含 model_variant + gray_ratio"]
```

**关键文件：**

- `backend/app/config.py` — `NEW_MODEL_RATIO = 5`
- `backend/app/services/model_manager.py` — `should_use_new_model()`, `register_model_version()`, `rollback_model()`
- `backend/models/model_metadata.json` — 活跃版本与历史记录

---

## 6. 数据安全架构

```mermaid
flowchart LR
    subgraph Frontend["前端（浏览器）"]
        Input["用户输入持仓"]
        Encrypt["portfolioCrypto.ts<br/>AES-256 + SHA256 派生密钥"]
        Store["localStorage<br/>enc:v1:{ciphertext}"]
    end

    subgraph Backend["后端（服务端）"]
        Env[".env 环境变量<br/>TUSHARE / DEEPSEEK / SECRET_KEY"]
        Fernet["crypto.py Fernet 加密"]
        DB["SQLite 审计库<br/>不含持仓明文"]
    end

    Input --> Encrypt --> Store
    Store -.->|诊断时仅发送代码/价格| Backend
    Env --> Backend
```

**设计原则：**

- 持仓默认**不上传云端**，仅存本地加密  
- 诊断 API 仅接收资产代码与用户填写的价格  
- API Key 仅存服务端 `.env`，前端零接触  
- 用户可随时「清除本地数据」  

---

## 7. 数据库模型（核心表）

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `audit_logs` | 诊断审计日志 | request_id, step_name, status, detail, created_at |
| `compliance_logs` | 合规拦截记录 | action, matched_word, question, created_at |
| `portfolios` | 服务端持仓（可选） | user_id, assets_json |

---

## 8. 部署架构

```mermaid
flowchart TB
    User["用户浏览器"] -->|:80| Nginx["Nginx 容器<br/>frontend"]
    Nginx -->|"/api/*"| FastAPI["FastAPI 容器<br/>backend:8000"]
    FastAPI --> SQLite["Docker Volume<br/>lingxi.db"]
    FastAPI --> Models["挂载 models/<br/>只读"]
    FastAPI --> Tushare["Tushare API"]
    FastAPI --> DeepSeek["DeepSeek API"]
```
