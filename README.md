# 灵析 - AI智能投顾助手

基于四层工业级架构的AI理财辅助工具

## 产品定位

灵析是一款人机协同的AI理财辅助工具，通过AI技术帮助用户更好地理解持仓、识别风险、学习理财知识，同时严格遵守AI能力边界，确保合规合法。

## 四大设计原则

1. **人机协同原则**：AI负责数据处理，用户做最终决策
2. **AI边界管控原则**：明确AI能做什么、不能做什么
3. **可解释性原则**：所有结论附带数据来源和分析维度
4. **分层风控原则**：数据层、AI输出层、交互层三重防护

## 技术架构

### 前端
- Vue 3 + Vite + TypeScript
- TailwindCSS
- Pinia 状态管理
- Vue Router

### 后端
- Python FastAPI
- SQLite + SQLAlchemy
- Pandas 数据处理

### 模型层
- TensorFlow/Keras (LSTM时序模型)
- Scikit-learn (随机森林)
- LLM API (文本分析)

## 核心功能模块

1. **AI持仓智能诊断**：自动识别持仓资产，分析风险点和机会
2. **AI资产周期择时辅助**：基于LSTM分析估值周期阶段
3. **AI投资情绪纠偏**：实时监测市场情绪，理性引导
4. **场景化AI投教系统**：基于持仓的个性化理财知识
5. **AI分析依据溯源页**：展示每条结论的溯源信息
6. **风控规则兜底展示面板**：展示合规校验规则

## 快速启动

### 使用Docker Compose

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，填入必要的API密钥

# 一键启动
./start.sh
```

### 手动启动

**前端**
```bash
cd frontend
pnpm install
pnpm dev
```

**后端**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 项目结构

```
lingxi-ai-advisor/
├── frontend/          # Vue3前端
├── backend/           # FastAPI后端
├── docker-compose.yml
└── start.sh
```

## 合规声明

- AI分析仅供参考，不构成投资建议
- 历史收益不代表未来表现
- AI无法预测市场
- 所有投资决策由用户自主做出

## License

MIT
