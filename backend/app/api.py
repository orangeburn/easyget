from fastapi import APIRouter, Request, HTTPException
import asyncio
import time
from typing import Dict, Any, List
from app.schemas.constraint import BusinessConstraint
from app.schemas.clue import ClueItem
from app.core.state import state
from app.services.task_service import task_service
from app.utils.logger import debug_log
from app.core.system_settings import load_system_settings, update_system_settings, test_system_settings
from app.schemas.system_settings import SystemSettingsPayload, SystemSettingsResponse, SystemSettingsTestResponse

router = APIRouter()

@router.get("/state")
async def get_system_state():
    """获取当前系统状态（配置、进度等）"""
    def build_state_payload():
        constraint = state.constraint
        return {
            "has_constraint": constraint is not None,
            "is_running": state.is_running,
            "is_paused": state.is_paused,
            "current_progress": state.current_progress,
            "current_step": state.current_step,
            "company_name": constraint.company_name if constraint else None,
            "search_keywords": " ".join(constraint.core_business) if constraint and constraint.core_business else "",
            "target_urls": "\n".join(constraint.custom_urls) if constraint and constraint.custom_urls else "",
            "wechat_accounts": "\n".join(constraint.wechat_accounts) if constraint and constraint.wechat_accounts else "",
            "geography_limits": constraint.geography_limits if constraint else [],
            "financial_thresholds": constraint.financial_thresholds if constraint else [],
            "other_constraints": constraint.other_constraints if constraint else [],
            "scan_frequency": constraint.scan_frequency if constraint else 1440,
            "expanded_keywords": state.last_expanded_keywords
        }

    return await asyncio.to_thread(build_state_payload)

@router.post("/task/run")
async def run_collection_and_analysis(payload: Dict[str, Any]):
    """
    执行：启动信息采集并用极简 Pipeline 过滤
    Payload 结构: { "constraint": ..., "strategy": ... }
    """
    debug_log(f"API /task/run invoked. Total payload size: {len(str(payload))}")
    
    # 1. 解析并持久化手动画像
    constraint_data = payload.get("constraint")
    if constraint_data:
        try:
            new_constraint = BusinessConstraint(**constraint_data)
            state.update_constraint(new_constraint)
            debug_log(f"Synced manual profile: {new_constraint.company_name}")
        except Exception as e:
            debug_log(f"Profile sync failed: {e}")

    # 2. 解析采集策略
    strategy = payload.get("strategy", {})

    # 如果已有任务在跑，先终止旧任务，确保新配置生效（不影响自动循环）
    try:
        task_service.cancel_current_task()
    except Exception as e:
        debug_log(f"Task cancel failed before restart: {e}")
    await asyncio.sleep(0)
    
    # 立即标记状态，防止前端轮询到“空闲”
    state.is_running = True
    state.is_paused = False
    state.current_progress = 5
    state.current_step = "正在启动抓取任务..."

    debug_log(f"Dispatching task context keywords: {strategy.get('search_keywords', 'N/A')}")
    asyncio.create_task(task_service.run_one_off_scan(strategy))
    
    return {"status": "Task dispatched", "is_running": True}

@router.post("/task/stop")
async def stop_collection():
    """用户暂停任务"""
    task_service.request_stop()
    state.is_paused = True
    state.is_running = False
    state.current_progress = 0
    state.current_step = "已暂停"
    return {"status": "Task stopped", "is_running": False}

@router.get("/settings", response_model=SystemSettingsResponse)
async def get_system_settings():
    """获取系统设置（模型/搜索 API 配置）"""
    return load_system_settings()

@router.post("/settings", response_model=SystemSettingsResponse)
async def save_system_settings(payload: SystemSettingsPayload):
    """保存系统设置并立即生效"""
    return update_system_settings(payload.model_dump())

@router.post("/settings/test", response_model=SystemSettingsTestResponse)
async def test_settings(payload: SystemSettingsPayload):
    """测试系统设置连接是否可用（不写入数据库）"""
    return await test_system_settings(payload.model_dump())

@router.get("/clues", response_model=List[ClueItem])
async def get_clues():
    """获取已发现的线索列表"""
    return await asyncio.to_thread(lambda: state.clues)

@router.get("/clues/stream")
async def stream_clues(request: Request):
    """SSE: 每处理一条线索就推送到前端"""
    import asyncio
    import json
    from fastapi.responses import StreamingResponse

    queue = state.subscribe_clues()

    async def event_generator():
        try:
            # Initial ping so client knows stream is alive
            yield "event: ready\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive
                    yield ": ping\n\n"
        finally:
            state.unsubscribe_clues(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/clues/{clue_id}/feedback")
async def update_clue_feedback(clue_id: str, payload: Dict[str, Any]):
    """更新线索的用户反馈状态"""
    feedback = payload.get("feedback")
    archived = payload.get("archived")
    started_at = time.perf_counter()
    await asyncio.to_thread(state.update_clue_status, clue_id, feedback=feedback, archived=archived)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    if elapsed_ms > 1000:
        debug_log(f"Clue feedback update slow: clue_id={clue_id}, elapsed_ms={elapsed_ms:.0f}")
    return {"status": "success"}

@router.get("/clues/export")
async def export_clues_csv():
    """将线索导出为 CSV 格式"""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    clues = state.clues
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "标题", "来源", "链接", "一票否决原因", "创建时间"])
    
    for c in clues:
        writer.writerow([
            c.id,
            c.title,
            c.source,
            c.url,
            c.veto_reason or "",
            c.created_at
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=easyget_clues.csv"}
    )

@router.post("/clues/export")
async def export_selected_clues_csv(payload: Dict[str, Any]):
    """将选中的线索导出为 CSV 格式"""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from app.core.database import SessionLocal, ClueModel

    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="未提供任何线索")

    # 去重并保持顺序
    ordered_ids = []
    seen = set()
    for cid in ids:
        if cid in seen:
            continue
        seen.add(cid)
        ordered_ids.append(cid)

    db = SessionLocal()
    try:
        models = db.query(ClueModel).filter(ClueModel.id.in_(ordered_ids)).all()
        model_map = {m.id: m for m in models}
    finally:
        db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "标题", "来源", "链接", "一票否决原因", "创建时间"])

    for cid in ordered_ids:
        m = model_map.get(cid)
        if not m:
            continue
        writer.writerow([
            m.id,
            m.title,
            m.source,
            m.url,
            m.veto_reason or "",
            m.created_at
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=easyget_clues_selected.csv"}
    )
