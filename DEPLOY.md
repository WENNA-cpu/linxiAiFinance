# 灵析 — 阿里云 / 秒悟 部署指南

## 方式一：秒悟（CodeBuddy）一键部署（推荐面试演示）

1. 在秒悟/CodeBuddy 中打开本项目
2. 点击 **「部署」→「一键部署到阿里云」**
3. 选择 **Docker Compose** 或 **全栈应用** 模板
4. 配置环境变量（部署面板中填写）：
   - `TUSHARE_TOKEN` — Tushare 行情 Token
   - `DEEPSEEK_API_KEY` — 投教 AI 问答
   - `SECRET_KEY` — 随机字符串
5. 部署完成后复制 **公网访问链接**，形如：
   - `https://xxx.codebuddy.app` 或
   - `http://<ECS公网IP>`

> 部署前请确认 `backend/models/` 下已有 `lstm_cycle.h5` 和 `rf_risk.pkl`（已训练）。

## 方式二：阿里云 ECS + Docker Compose

### 1. 购买 ECS

- 规格：2核4G 即可
- 系统：Ubuntu 22.04
- 安全组：开放 **80**、**443**（可选）

### 2. 上传代码并部署

```bash
git clone <你的仓库> lingxi
cd lingxi
cp .env.example .env
# 编辑 .env 填入密钥

chmod +x deploy.sh
./deploy.sh
```

### 3. 验证

```bash
curl http://localhost/api/health
# 期望: {"status":"healthy"}
```

浏览器访问 `http://<ECS公网IP>/`

### 4. 演示路径（写进简历）

1. 首页 → **持仓诊断** → 导入/诊断
2. 诊断完成 → **查看分析溯源**
3. 溯源页展示 **7 步真实审计日志**（来自 SQLite）
4. **资产周期分析** → LSTM 预测 + 置信区间
5. **投教页** → AI 问答助手

## 方式三：本地 Docker 预览

```bash
docker compose up --build -d
# 访问 http://localhost
```

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| TUSHARE_TOKEN | 是 | 行情与估值数据 |
| DEEPSEEK_API_KEY | 是 | 投教 AI 问答 |
| SECRET_KEY | 是 | 应用密钥 |
| NEW_MODEL_RATIO | 否 | 新模型灰度比例，默认 5% |

## 常见问题

**Q: 溯源页只有 1 条日志？**  
A: 需先完成一次「持仓诊断」，使用返回的 `request_id` 访问 `/trace/{id}`，勿用 demo ID。

**Q: 模型预测不可用？**  
A: 确认 `backend/models/lstm_cycle.h5` 和 `rf_risk.pkl` 已挂载进容器。

**Q: AI 问答 503？**  
A: 检查 `DEEPSEEK_API_KEY` 与账户余额。
