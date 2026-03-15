from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException
from app.schemas.constraint import BusinessConstraint, DynamicFormSchema
from app.engines.parser import DynamicFormParser
from app.core.state import state
from app.services.task_service import task_service
from app.services.file_processor import file_processor
from typing import Dict, Any, List
from app.schemas.clue import ClueItem
from openai import AuthenticationError
from app.utils.logger import debug_log

router = APIRouter()
parser_engine = DynamicFormParser()

@router.post("/parser/upload")
async def upload_document(file: UploadFile = File(...)):
    """从上传的文件（docx, txt, md）中提取文本"""
    content = await file.read()
    text = file_processor.extract_text(content, file.filename)
    
    if text is None:
        raise HTTPException(status_code=400, detail="Unsupported file format or error during parsing")
        
    return {"text": text, "filename": file.filename}

@router.get("/state")
async def get_system_state():
    """获取当前系统状态（配置、进度等）"""
    return {
        "has_constraint": state.constraint is not None,
        "is_running": state.is_running,
        "current_progress": state.current_progress,
        "current_step": state.current_step,
        "company_name": state.constraint.company_name if state.constraint else None
    }

@router.post("/parser/initial", response_model=BusinessConstraint)
async def parse_initial_document(payload: Dict[str, str]):
    """步骤1：从上传的文本资料解析生成基础画像"""
    text = payload.get("text", "")
    try:
        constraint = parser_engine.parse_initial_document(text)
        state.update_constraint(constraint)
        return constraint
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="OpenAI API Key 无效，请检查 .env 配置")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@router.post("/parser/form", response_model=DynamicFormSchema)
async def generate_dynamic_form(constraint: BusinessConstraint):
    """步骤2：利用行业信息推算，生成动态表单"""
    form_schema = parser_engine.generate_dynamic_form(constraint)
    return form_schema

@router.post("/parser/update", response_model=BusinessConstraint)
async def update_constraint(payload: Dict[str, Any]):
    """步骤3：用户提交表单，融合画像并返回最终结果"""
    constraint_dict = payload.get("constraint", {})
    form_data = payload.get("form_data", {})
    
    try:
        constraint = BusinessConstraint(**constraint_dict)
        updated_constraint = parser_engine.update_constraint_from_form(constraint, form_data)
        state.update_constraint(updated_constraint)
        return updated_constraint
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="OpenAI API Key 无效")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存与画像融合失败: {str(e)}")

@router.post("/parser/keywords")
async def generate_keywords(constraint: BusinessConstraint):
    """根据画像生成推荐的搜索关键词"""
    keywords = parser_engine.generate_keywords(constraint)
    return {"keywords": keywords}

@router.post("/task/run")
async def run_collection_and_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    执行：启动信息采集并用 Pipeline 分析清洗
    Payload 结构: { "constraint": ..., "strategy": ... }
    """
    debug_log(f"API /task/run invoked. Total payload size: {len(str(payload))}")
    
    # 1. 解析并持久化画像 (如果前端提供了全量画像)
    constraint_data = payload.get("constraint")
    if constraint_data:
        try:
            from app.schemas.constraint import BusinessConstraint
            new_constraint = BusinessConstraint(**constraint_data)
            state.update_constraint(new_constraint)
            debug_log(f"Synced enterprise profile: {new_constraint.company_name}")
        except Exception as e:
            debug_log(f"Profile sync failed: {e}")

    # 2. 解析采集策略
    strategy = payload.get("strategy", {})
    
    # 立即标记状态，防止前端轮询到“空闲”
    state.is_running = True
    state.current_progress = 5
    state.current_step = "正在启动抓取任务..."
    
    # 3. 将其余配置并入策略触发后台任务
    # 补充：如果 strategy 中没有关键词，尝试从画像中取
    if not strategy.get("search_keywords") and state.constraint:
        strategy["search_keywords"] = f"{state.constraint.company_name} 招标"

    debug_log(f"Dispatching task context keywords: {strategy.get('search_keywords', 'N/A')}")
    background_tasks.add_task(task_service.run_one_off_scan, strategy)
    
    return {"status": "Task dispatched", "is_running": True}

@router.get("/clues", response_model=List[ClueItem])
async def get_clues():
    """获取已发现的线索列表"""
    return state.clues

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
    writer.writerow(["ID", "标题", "来源", "链接", "匹配分", "一票否决原因", "项目金额", "截止时间", "创建时间"])
    
    for c in clues:
        meta = c.extracted_metadata or {}
        writer.writerow([
            c.id,
            c.title,
            c.source,
            c.url,
            c.match_score,
            c.veto_reason or "",
            meta.get("budget", ""),
            meta.get("deadline", ""),
            c.created_at
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=easyget_clues.csv"}
    )
