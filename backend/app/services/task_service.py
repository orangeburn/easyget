import asyncio
from typing import Dict, Any
from app.engines.collector.dispatcher import CollectionDispatcher
from app.engines.analyzer.pipeline import CluePipeline
from app.core.state import state
from app.utils.logger import debug_log

class TaskService:
    def __init__(self):
        self.dispatcher = CollectionDispatcher()
        self.pipeline = CluePipeline()

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
            if is_scheduled and not config:
                constraint = state.constraint
                if constraint:
                    config = {
                        "search_keywords": f"{constraint.company_name} 招标"
                    }
                else:
                    config = {}

            if state.constraint is None:
                debug_log("TaskService: Missing constraint; aborting run_one_off_scan")
                state.current_progress = 0
                state.current_step = "错误: 未配置企业画像"
                return

            debug_log("TaskService: Calling Dispatcher.run_all_tasks")
            raw_clues = await self.dispatcher.run_all_tasks(state.constraint, config)
            state.current_progress = 50
            state.current_step = f"采集完成，共 {len(raw_clues)} 条，正在进行 AI 深度分析..."
            debug_log(f"TaskService: Collection done. Got {len(raw_clues)} raw clues")

            # 2. 分析
            processed_clues = await self.pipeline.run(raw_clues, state.constraint)
            state.current_progress = 90
            state.current_step = "分析完成，正在同步结果..."

            # 3. 持久化结果
            state.add_clues(processed_clues)
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

task_service = TaskService()
