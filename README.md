# Easyget

## 项目简介
Easyget 是一个面向招标/采购信息的“Agentic Workflow + 结构化抓取”工具，包含：
- HTML → Markdown Reader
- 结构化抽取（Markdown 输入 + JSON 校验）
- 规则评分 + 语义评分融合
- 前端“判定墙”反馈闭环

---

## 目录结构
- `backend/` FastAPI 后端
- `frontend/` Vite + React 前端
- `easyget.db` SQLite 数据库（本地生成）

---

## 启动命令

后端（`backend` 目录）：

```powershell
cd backend
$env:PYTHONPATH="e:\Exercise\VibeCode\Easyget\backend\.deps"
python run.py
```

前端（`frontend` 目录）：

```powershell
cd frontend
npm run dev
```

默认地址：
- 后端 API：`http://127.0.0.1:8000/api`
- 前端页面：`http://127.0.0.1:5173`

判定墙入口：`/dashboard/wall`

---

## 环境变量
建议使用 `.env.local`，避免提交敏感信息：

```
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4-turbo-preview
```

---

## 依赖安装（后端）
本项目后端依赖安装到 `backend/.deps`，启动时通过 `PYTHONPATH` 引用：

```powershell
python -m pip install -r backend\requirements.txt -t backend\.deps
```

---

## 测试
后端：
```powershell
cd backend
$env:PYTHONPATH="e:\Exercise\VibeCode\Easyget\backend\.deps"
python -m pytest
```

前端构建：
```powershell
cd frontend
npm run build
```

---

## 常见问题
1. 启动后端时报 `python-multipart` 缺失  
   运行：
   ```powershell
   python -m pip install python-multipart==0.0.9 -t backend\.deps
   ```
2. Vite 报 `spawn EPERM`  
   一般为 Windows 权限/环境限制导致的进程创建失败，建议以管理员权限运行终端或更换 Node 版本测试。
