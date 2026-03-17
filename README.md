# Easyget (极简版)

## 项目简介
Easyget 是一个高性能、低干扰的招标/采购线索搜集与人工清洗工具。相比于复杂的 AI 端到端方案，本项目采用**“自动化搜集 + 规则初筛 + 人工最终决策”**的极简工作流，确保获取到的招标信息 100% 真实且时效性强。

### 核心功能
- **极简配置**：只需填入关键词或监控网址，无需训练复杂的业务画像。
- **流式输出**：采集与分析完成一条就推送一条（SSE 实时更新，无需等待全量结束）。
- **标题语义过滤**：仅基于标题进行 LLM 过滤（失败时自动降级为放行）。
- **结构化硬过滤**：目标省市/金额/发布时间等规则在采集后立即生效。
- **强制时效过滤**：内置搜索引擎时间锁，优先获取近 30 天内的最新信息（qdr:m）。
- **微信专项攻坚**：支持对微信公众号进行定向采集，解决微信内容闭环问题。
- **高效判定墙**：直观的线索列表，支持实时流式更新。
- **配置持久化**：支持“重新配置”时的全量回填，配置体验顺滑。

---

## 目录结构
- `backend/` FastAPI 后端（核心爬虫引擎、SQLite 持久化）
- `frontend/` Vite + React 前端（任务配置中心、数据判定墙）
- `easyget.db` 本地 SQLite 数据库

---

## 启动指南

### 1. 准备工作 (环境变量)
在 `backend/` 目录下创建 `.env` 文件，配置核心搜索能力：

```env
# LLM（用于关键词扩展与标题过滤，可选但建议配置）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4-turbo-preview

# 搜索引擎（可选）
SEARCH_API_KEY=your_serper_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
# 可选：如需使用特定代理或备用搜索引擎
# WEB_PROXY_URL=...
```

### 2. 后端启动
```powershell
cd backend
# 安装依赖到本地目录 (如果未安装过)
python -m pip install -r requirements.txt -t .deps
# 设置 PYTHONPATH 并运行
$env:PYTHONPATH="e:\Exercise\VibeCode\Easyget\backend\.deps"
python run.py
```

### 3. 前端启动
```powershell
cd frontend
npm install
npm run dev
```

---

## 核心工作流
1. **任务配置**：在首页填入关键词（如：`广州 智慧医疗 招标`）或定向网址。
2. **自动化搜集**：系统分流至 Serper / Tavily / 浏览器搜索（百度/Bing/搜狗）及微信并发采集。
3. **实时过滤**：采集到一条就进行标题 LLM 过滤 + 结构化规则过滤。
4. **流式更新**：前端通过 SSE 接收逐条结果并即时展示。
5. **数据同步**：结果实时落库，支持导出或集成。

---

## 常见问题
- **数据加载不出来？** 请检查 `backend/.env` 是否配置了有效的 `SEARCH_API_KEY`。
- **LLM 无法调用？** 请检查 `OPENAI_API_KEY` 是否有效；无效时会自动降级（关键词不扩展、标题过滤放行）。
- **Windows 下 Vite 报错？** 建议检查 node 版本是否满足 Vite 4+ 要求，并清理 `node_modules` 重新安装。
