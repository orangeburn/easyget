from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.state import state
import logging

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
            self.scheduler.shutdown()
            logger.info("Scheduler shut down.")

    def schedule_scan(self, minutes: int):
        """配置或重新配置定时扫描周期"""
        from app.services.task_service import task_service
        
        # 如果任务已存在，先移除
        if self.scheduler.get_job(self.job_id):
            self.scheduler.remove_job(self.job_id)
            logger.info(f"Removed existing job: {self.job_id}")

        # 自动循环模式（minutes <= 0）
        if minutes <= 0:
            task_service.start_auto_loop()
            logger.info("Auto loop enabled (no fixed interval).")
            return

        # 定时模式：确保自动循环停止
        task_service.stop_auto_loop()

        # 添加新任务
        self.scheduler.add_job(
            task_service.run_one_off_scan,
            trigger=IntervalTrigger(minutes=minutes),
            id=self.job_id,
            kwargs={"is_scheduled": True}, # 标记为自动调度运行
            replace_existing=True
        )
        logger.info(f"Scheduled scan job every {minutes} minutes.")

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
