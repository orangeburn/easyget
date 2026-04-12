from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.state import state
from app.utils.logger import debug_log
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.job_id = "main_scan_job"

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started.")

    def shutdown(self):
        try:
            from app.services.task_service import task_service
            task_service.stop_auto_loop()
        except Exception:
            pass
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down.")

    def schedule_scan(self, minutes: int, trigger_missed_today: bool = False, activate: bool = True):
        """配置或重新配置定时扫描周期。
        activate=False 时仅更新配置，不触发任何执行（用于服务启动阶段恢复状态）。
        """
        from app.services.task_service import task_service
        minutes = 0 if minutes == 0 else 1440
        debug_log(
            f"Scheduler: schedule_scan(minutes={minutes}, "
            f"trigger_missed_today={trigger_missed_today}, activate={activate})"
        )
        
        # 如果任务已存在，先移除
        if self.scheduler.get_job(self.job_id):
            self.scheduler.remove_job(self.job_id)
            logger.info(f"Removed existing job: {self.job_id}")
            debug_log(f"Scheduler: removed existing job {self.job_id}")

        # 自动循环模式（minutes <= 0）
        if minutes <= 0:
            if not activate:
                task_service.stop_auto_loop()
                debug_log("Scheduler: auto loop not activated (activate=False)")
                return
            task_service.start_auto_loop()
            logger.info("Auto loop enabled (no fixed interval).")
            debug_log("Scheduler: auto loop enabled")
            return

        # 每天模式：不做固定时刻调度，仅保留“启动时补跑一次（若今天未跑）”
        # 先确保自动循环停止
        task_service.stop_auto_loop()
        debug_log("Scheduler: auto loop stopped (daily mode, no fixed-time schedule)")

        if trigger_missed_today and activate:
            last_scan_at = state.get_last_scan_at()
            today = datetime.now().date()
            if (last_scan_at is None) or (last_scan_at.date() != today):
                debug_log("Scheduler: daily mode startup catch-up triggered")
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(task_service.run_one_off_scan(is_scheduled=True))
                except Exception as e:
                    debug_log(f"Scheduler: failed to trigger startup catch-up - {e}")
            else:
                debug_log("Scheduler: daily mode startup catch-up skipped (already ran today)")
        elif trigger_missed_today and not activate:
            debug_log("Scheduler: catch-up skipped because activate=False")

    def schedule_cleanup(self):
        """每12小时清理一次过期线索"""
        from app.services.task_service import task_service
        job_id = "cleanup_job"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        self.scheduler.add_job(
            task_service.cleanup_expired_clues,
            trigger=IntervalTrigger(hours=12),
            id=job_id,
            replace_existing=True
        )
        logger.info("Scheduled cleanup job every 12 hours.")

scheduler_manager = TaskScheduler()
