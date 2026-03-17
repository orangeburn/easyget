import asyncio
from typing import Dict, Any, List
from app.engines.collector.dispatcher import CollectionDispatcher
from app.engines.analyzer.pipeline import CluePipeline
from app.services.llm_service import LLMService
from app.core.state import state
from app.utils.logger import debug_log

class TaskService:
    def __init__(self):
        self.dispatcher = CollectionDispatcher()
        self.pipeline = CluePipeline()
        self.llm = LLMService()

    async def run_one_off_scan(self, config: Dict[str, Any] = None, is_scheduled: bool = False):
        """
        执行一次全量扫描与分析
        """
        # 如果是定时任务，需要检查是否正在运行
        if is_scheduled and state.is_running:
            debug_log("TaskService: Skip scheduled scan (already running)")
            return
        
        # API 主动触发时，state.is_running 可能已经被 API 线程置为 True 以提供即时反馈
        state.is_running = True
        state.current_progress = 10
        state.current_step = "定时任务启动中..." if is_scheduled else "正在启动混合采集器..."
        debug_log(f"TaskService: run_one_off_scan start (is_scheduled={is_scheduled})")
        
        try:
            # 1. 采集
            # 确保 config 不为空
            if not config: config = {}
            
            search_keywords = config.get("search_keywords", "")
            
            # 如果有初项关键词，利用 LLM 进行扩充
            if search_keywords:
                state.current_step = f"正在扩充关键词: {search_keywords}..."
                debug_log(f"TaskService: Expanding keywords '{search_keywords}' via LLM")
                expanded = await self._expand_keywords_via_llm_async(search_keywords, timeout_s=12.0)
                if expanded:
                    debug_log(f"TaskService: Expanded keywords: {expanded}")
                    config["search_keywords"] = ",".join(expanded)
                else:
                    debug_log("TaskService: Keyword expansion timeout/failed, using original keywords")
            elif is_scheduled:
                constraint = state.constraint
                if constraint:
                    config["search_keywords"] = f"{constraint.company_name} 招标"
                else:
                    config["search_keywords"] = ""

            if not state.constraint:
                debug_log("TaskService: !!! ABORT !!! - state.constraint is None")
                state.current_progress = 0
                state.current_step = "错误: 系统画像未激活"
                return

            state.current_progress = 20
            state.current_step = "正在执行采集任务（全网搜索/站点/公众号）..."
            debug_log(f"TaskService: Executing scan with config: {config}")
            # 2. 流式处理：采集到即过滤并推送（只输出 LLM 过滤后的结果）
            clue_queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
            done_event = asyncio.Event()

            def on_clue(clue):
                try:
                    clue_queue.put_nowait(clue)
                except Exception:
                    pass

            analyzer_task = asyncio.create_task(
                self.pipeline.run_stream(clue_queue, done_event, state.constraint)
            )

            raw_clues = await self.dispatcher.run_all_tasks_stream(state.constraint, config, on_clue=on_clue)
            done_event.set()
            await analyzer_task

            state.current_progress = 90
            state.current_step = f"分析完成，共处理 {len(raw_clues)} 条，正在同步结果..."
            state.current_progress = 100
            state.current_step = "完成"
        except Exception as e:
            import traceback
            debug_log(f"TaskService: !!! CRASH !!! - {type(e).__name__}: {str(e)}")
            traceback_str = traceback.format_exc()
            debug_log(f"Stack Trace:\n{traceback_str}")
            state.current_step = f"错误: {str(e)}"
        finally:
            state.is_running = False

    async def cleanup_expired_clues(self):
        """物理删除超过3天且处于已过滤状态（无人工反馈）的线索"""
        from app.core.database import SessionLocal, ClueModel
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            three_days_ago = datetime.now() - timedelta(days=3)
            # 过滤逻辑：创建时间 < 3天 AND 有否决原因 AND 无人工动作(feedback=0)
            query = db.query(ClueModel).filter(
                ClueModel.created_at < three_days_ago,
                ClueModel.veto_reason != None,
                ClueModel.user_feedback == 0
            )
            count = query.count()
            if count > 0:
                query.delete(synchronize_session=False)
                db.commit()
                debug_log(f"TaskService: Cleanup deleted {count} expired filtered clues")
            else:
                debug_log("TaskService: No expired clues to clean")
        except Exception as e:
            db.rollback()
            debug_log(f"TaskService: Cleanup failed - {e}")
        finally:
            db.close()

    def _expand_keywords_via_llm(self, original_keywords: str) -> List[str]:
        """利用 LLM 扩展搜索关键词"""
        system_prompt = """
你是搜索引擎专家。请将用户提供的关键词扩展为 5-8 个用于寻找招标、采购、项目机会的专业搜索词。
直接返回 JSON 对象，格式为 {"keywords": ["...", "..."]}。
示例输入: "充电桩"
示例输出: {"keywords": ["充电桩采购公告", "直流充电桩招标", "充电站建设工程", "新能源车充电桩采购", "充电桩中标结果"]}
"""
        try:
            # 增加超时逻辑 (模拟，如果 LLMService 不支持则在此捕获)
            result = self.llm.extract_structured_data(
                system_prompt=system_prompt,
                user_input=f"扩展以下关键词: {original_keywords}",
                response_format=None
            )
            if isinstance(result, dict) and "keywords" in result:
                return result["keywords"]
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            debug_log(f"TaskService: Keyword expansion failed (fallback to original) - {e}")
            return []

    async def _expand_keywords_via_llm_async(self, original_keywords: str, timeout_s: float = 12.0) -> List[str]:
        """异步包装 + 超时保护，避免关键词扩充卡死主流程"""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._expand_keywords_via_llm, original_keywords),
                timeout=timeout_s
            )
        except asyncio.TimeoutError:
            debug_log(f"TaskService: Keyword expansion timeout after {timeout_s}s (fallback to original)")
            return []

task_service = TaskService()
