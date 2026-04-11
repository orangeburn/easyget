import asyncio
from typing import Dict, Any, List
from app.engines.collector.dispatcher import CollectionDispatcher
from app.engines.analyzer.pipeline import CluePipeline
from app.services.llm_service import LLMService
from app.core.state import state
from app.utils.logger import debug_log
from app.utils.keywords import (
    build_fallback_expanded_keywords,
    dedupe_keywords,
    merge_keywords,
    split_search_keywords,
)

class TaskService:
    def __init__(self):
        self.dispatcher = CollectionDispatcher()
        self.pipeline = CluePipeline()
        self.llm = LLMService()
        self._current_task: asyncio.Task | None = None
        self._auto_loop_task: asyncio.Task | None = None
        self._stop_requested: bool = False

    def start_auto_loop(self):
        if self._auto_loop_task and not self._auto_loop_task.done():
            return
        self._stop_requested = False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self._auto_loop_task = loop.create_task(self._auto_loop_runner())

    def stop_auto_loop(self):
        self._stop_requested = True
        if self._auto_loop_task and not self._auto_loop_task.done():
            self._auto_loop_task.cancel()
        self._auto_loop_task = None

    def request_stop(self):
        self._stop_requested = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        if self._auto_loop_task and not self._auto_loop_task.done():
            self._auto_loop_task.cancel()
        self._auto_loop_task = None

    async def wait_for_stop(self, timeout_s: float = 5.0):
        """Best-effort wait for running background tasks to stop during shutdown."""
        pending = []
        if self._current_task and not self._current_task.done():
            pending.append(self._current_task)
        if self._auto_loop_task and not self._auto_loop_task.done():
            pending.append(self._auto_loop_task)
        if not pending:
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError:
            debug_log(f"TaskService: Shutdown wait timed out after {timeout_s}s")

    def cancel_current_task(self):
        """仅取消当前扫描任务，不影响自动循环调度。"""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    async def _auto_loop_runner(self):
        debug_log("TaskService: Auto loop started")
        while not self._stop_requested:
            await self.run_one_off_scan(is_scheduled=True)
            # 短暂歇息，避免紧密循环
            await asyncio.sleep(5)
        debug_log("TaskService: Auto loop stopped")

    async def run_one_off_scan(self, config: Dict[str, Any] = None, is_scheduled: bool = False):
        """
        执行一次全量扫描与分析
        """
        # 如果是定时任务，需要检查是否正在运行
        if is_scheduled and state.is_running:
            debug_log("TaskService: Skip scheduled scan (already running)")
            return
        if is_scheduled and state.is_paused:
            debug_log("TaskService: Skip scheduled scan (paused)")
            return
        
        # API 主动触发时，state.is_running 可能已经被 API 线程置为 True 以提供即时反馈
        state.is_running = True
        state.is_paused = False
        state.current_progress = 10
        state.current_step = "定时任务启动中..." if is_scheduled else "正在启动混合采集器..."
        debug_log(f"TaskService: run_one_off_scan start (is_scheduled={is_scheduled})")
        self._current_task = asyncio.current_task()
        
        try:
            # 1. 采集
            # 确保 config 不为空
            if not config: config = {}
            
            search_keywords = config.get("search_keywords", "")
            base_keywords = split_search_keywords(search_keywords)
            
            # 如果有初项关键词，利用 LLM 进行扩充
            if base_keywords:
                state.current_step = f"正在扩充关键词: {search_keywords}..."
                debug_log(f"TaskService: Expanding keywords '{search_keywords}' via LLM")
                expanded = await self._expand_keywords_via_llm_async(search_keywords, timeout_s=12.0)
                if expanded:
                    effective_keywords = merge_keywords(base_keywords, expanded)
                    debug_log(f"TaskService: Expanded keywords: {effective_keywords}")
                    state.last_expanded_keywords = effective_keywords
                    config["search_keywords"] = ",".join(effective_keywords)
                else:
                    fallback_keywords = build_fallback_expanded_keywords(base_keywords)
                    debug_log(f"TaskService: Keyword expansion timeout/failed, using fallback keywords: {fallback_keywords}")
                    state.last_expanded_keywords = fallback_keywords
                    config["search_keywords"] = ",".join(fallback_keywords)
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
            try:
                raw_clues = await self.dispatcher.run_all_tasks_stream(state.constraint, config, on_clue=on_clue)
                done_event.set()
                await analyzer_task
            finally:
                if not done_event.is_set():
                    done_event.set()
                if analyzer_task and not analyzer_task.done():
                    analyzer_task.cancel()
                    try:
                        await analyzer_task
                    except asyncio.CancelledError:
                        pass

            state.current_progress = 90
            state.current_step = f"分析完成，共处理 {len(raw_clues)} 条，正在同步结果..."
            state.current_progress = 100
            state.current_step = "完成"
        except asyncio.CancelledError:
            debug_log("TaskService: Task cancelled by user")
            state.current_progress = 0
            # 仅在用户明确点击“暂停/停止”时进入 paused 状态；
            # 配置热更新/任务重启触发的取消不应阻断自动循环。
            if self._stop_requested:
                state.current_step = "已暂停"
                state.is_paused = True
            else:
                state.current_step = "任务重启中..."
                state.is_paused = False
            return
        except Exception as e:
            import traceback
            debug_log(f"TaskService: !!! CRASH !!! - {type(e).__name__}: {str(e)}")
            traceback_str = traceback.format_exc()
            debug_log(f"Stack Trace:\n{traceback_str}")
            state.current_step = f"错误: {str(e)}"
        finally:
            state.is_running = False
            if asyncio.current_task() == self._current_task:
                self._current_task = None

    async def cleanup_expired_clues(self):
        """物理删除超过7天且处于已过滤/已忽略状态的线索"""
        from app.core.database import SessionLocal, ClueModel
        from datetime import datetime, timedelta
        from sqlalchemy import or_, and_
        
        db = SessionLocal()
        try:
            seven_days_ago = datetime.now() - timedelta(days=7)
            # 过滤逻辑：创建时间 < 7天 AND (已过滤(有否决原因且未反馈) OR 已忽略)
            query = db.query(ClueModel).filter(
                ClueModel.created_at < seven_days_ago,
                or_(
                    and_(ClueModel.veto_reason != None, ClueModel.user_feedback == 0),
                    ClueModel.user_feedback.in_([2, -1])
                )
            )
            count = query.count()
            if count > 0:
                query.delete(synchronize_session=False)
                db.commit()
                debug_log(f"TaskService: Cleanup deleted {count} expired filtered/ignored clues")
            else:
                debug_log("TaskService: No expired filtered/ignored clues to clean")
        except Exception as e:
            db.rollback()
            debug_log(f"TaskService: Cleanup failed - {e}")
        finally:
            db.close()

    def _expand_keywords_via_llm(self, original_keywords: str) -> List[str]:
        """利用 LLM 扩展搜索关键词"""
        system_prompt = """
你是搜索引擎专家。用户会提供多个关键词，请针对每个关键词各扩展 2-3 个用于寻找招标、采购、项目机会的专业搜索词。
所有扩展词汇合并为一个数组返回，避免重复。
直接返回 JSON 对象，格式为 {"keywords": ["...", "..."]}。
示例输入: "充电桩, 储能"
示例输出: {"keywords": ["充电桩采购公告", "直流充电桩招标", "充电站建设工程", "储能系统采购公告", "储能项目招标", "储能设备采购"]}
"""
        try:
            # 增加超时逻辑 (模拟，如果 LLMService 不支持则在此捕获)
            result = self.llm.extract_structured_data(
                system_prompt=system_prompt,
                user_input=f"扩展以下关键词: {original_keywords}",
                response_format=None
            )
            if isinstance(result, dict) and "keywords" in result:
                values = result["keywords"]
                if isinstance(values, str):
                    return dedupe_keywords([values])
                if isinstance(values, list):
                    return dedupe_keywords(values)
            if isinstance(result, list):
                return dedupe_keywords(result)
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
