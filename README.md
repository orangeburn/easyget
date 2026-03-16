# Easyget (极简版)

## 项目简介
Easyget 是一个高性能、低干扰的招标/采购线索搜集与人工清洗工具。相比于复杂的 AI 端到端方案，本项目采用**“自动化搜集 + 规则初筛 + 人工最终决策”**的极简工作流，确保获取到的招标信息 100% 真实且时效性强。

### 核心功能
- **极简配置**：只需填入关键词或监控网址，无需训练复杂的业务画像。
- **强制时效过滤**：内置搜索引擎时间锁，强制只获取近 30 天内的最新信息（qdr:m）。
- **微信专项攻坚**：支持对微信公众号进行定向采集，解决微信内容闭环问题。
- **高效判定墙**：直观的线索列表，支持 15 秒自动轮询，实时刷新最新获取的线索。
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
# 必须：用于 Google 搜索
SEARCH_API_KEY=your_serper_api_key_here
# 可选：如需使用特定代理或备用搜索引擎
# PROXY_URL=...
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
2. **自动化搜集**：系统分流至 Serper (Google)、百度及微信进行并发采集。
3. **判定墙清洗**：数据流入 `/dashboard/wall`，用户进行“收藏”或“忽略”操作。
4. **数据同步**：支持判定结果实时落库，供后续导出或集成。

---

## 常见问题
- **数据加载不出来？** 请检查 `backend/.env` 是否配置了有效的 `SEARCH_API_KEY`。
- **Windows 下 Vite 报错？** 建议检查 node 版本是否满足 Vite 4+ 要求，并清理 `node_modules` 重新安装。

