from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from typing import Dict, Any, List
from app.schemas.constraint import BusinessConstraint
from app.schemas.clue import ClueItem
from app.core.state import state
from app.services.task_service import task_service
from app.utils.logger import debug_log

router = APIRouter()

@router.get("/state")
async def get_system_state():
    """获取当前系统状态（配置、进度等）"""
    return {
        "has_constraint": state.constraint is not None,
        "is_running": state.is_running,
        "current_progress": state.current_progress,
        "current_step": state.current_step,
        "company_name": state.constraint.company_name if state.constraint else None,
        "search_keywords": " ".join(state.constraint.core_business) if state.constraint and state.constraint.core_business else "",
        "target_urls": "\n".join(state.constraint.custom_urls) if state.constraint and state.constraint.custom_urls else "",
        "wechat_accounts": "\n".join(state.constraint.wechat_accounts) if state.constraint and state.constraint.wechat_accounts else "",
        "geography_limits": state.constraint.geography_limits if state.constraint else [],
        "financial_thresholds": state.constraint.financial_thresholds if state.constraint else [],
        "other_constraints": state.constraint.other_constraints if state.constraint else [],
        "scan_frequency": state.constraint.scan_frequency if state.constraint else 30
    }

@router.post("/task/run")
async def run_collection_and_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
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
    
    # 立即标记状态，防止前端轮询到“空闲”
    state.is_running = True
    state.current_progress = 5
    state.current_step = "正在启动抓取任务..."

    debug_log(f"Dispatching task context keywords: {strategy.get('search_keywords', 'N/A')}")
    background_tasks.add_task(task_service.run_one_off_scan, strategy)
    
    return {"status": "Task dispatched", "is_running": True}

@router.get("/clues", response_model=List[ClueItem])
async def get_clues():
    """获取已发现的线索列表"""
    return state.clues

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
    state.update_clue_status(clue_id, feedback=feedback, archived=archived)
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
