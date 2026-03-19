import asyncio
import os
import sys

# Ensure Playwright subprocesses work on Windows (Selector loop lacks subprocess support)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
import time
from contextlib import asynccontextmanager
from app.core.scheduler import scheduler_manager
from app.services.task_service import task_service
from app.core.state import state
from app.utils.logger import debug_log
from app.core.system_settings import load_system_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    debug_log("--- Server Lifespan Starting ---")
    try:
        loop = asyncio.get_running_loop()
        debug_log(f"AsyncIO loop: {loop.__class__.__name__}")
        debug_log(f"AsyncIO policy: {asyncio.get_event_loop_policy().__class__.__name__}")
    except Exception as e:
        debug_log(f"AsyncIO loop/policy check failed: {e}")
    # 加载系统设置（模型/搜索 API 等）
    load_system_settings()
    # 启动调度器
    scheduler_manager.start()
    
    # 获取已有画像并初始化定时任务
    constraint = state.constraint
    if constraint and constraint.scan_frequency:
        scheduler_manager.schedule_scan(constraint.scan_frequency)
    
    # 启动过清理任务
    scheduler_manager.schedule_cleanup()
    
    yield
    # 关闭
    try:
        task_service.request_stop()
    except Exception:
        pass
    scheduler_manager.shutdown()
    debug_log("--- Server Lifespan Shutdown ---")

app = FastAPI(
    title="Easyget Backend API",
    version="0.2.0",
    lifespan=lifespan
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    debug_log(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.2f}s")
    return response

# 配置 CORS 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null"],
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "instance_token": os.getenv("EASYGET_INSTANCE_TOKEN", "")
    }
