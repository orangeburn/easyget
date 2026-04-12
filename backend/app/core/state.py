from typing import List, Optional
from app.schemas.constraint import BusinessConstraint
from app.schemas.clue import ClueItem
from app.core.database import SessionLocal, ConstraintModel, ClueModel
from datetime import datetime
from fastapi.encoders import jsonable_encoder
import asyncio
from typing import Set
from app.utils.urls import sanitize_target_urls

def normalize_scan_frequency(value: Optional[int]) -> int:
    if value == 0:
        return 0
    if value == 1440:
        return 1440
    return 1440

class SystemState:
    def __init__(self):
        # 内存中仅保留轻量级状态
        self.is_running: bool = False
        self.is_paused: bool = False
        self.current_progress: int = 0
        self.current_step: str = "Ready"
        self._clue_subscribers: Set[asyncio.Queue] = set()
        self.last_expanded_keywords: List[str] = []

    @property
    def constraint(self) -> Optional[BusinessConstraint]:
        db = SessionLocal()
        try:
            model = db.query(ConstraintModel).order_by(ConstraintModel.updated_at.desc()).first()
            if model:
                return BusinessConstraint(
                    company_name=model.company_name,
                    core_business=model.core_business,
                    qualifications=model.qualifications,
                    geography_limits=model.geography_limits,
                    financial_thresholds=model.financial_thresholds,
                    other_constraints=model.other_constraints,
                    scan_frequency=normalize_scan_frequency(model.scan_frequency),
                    custom_urls=model.custom_urls or [],
                    wechat_accounts=model.wechat_accounts or [],
                    updated_at=model.updated_at or datetime.now()
                )
            return None
        finally:
            db.close()

    @property
    def clues(self) -> List[ClueItem]:
        # ... (unchanged)
        db = SessionLocal()
        try:
            models = db.query(ClueModel).order_by(ClueModel.created_at.desc()).all()
            return [
                ClueItem(
                    id=m.id,
                    title=m.title,
                    source=m.source,
                    url=m.url,
                    snippet=m.snippet,
                    publish_time=m.publish_time,
                    semantic_score=getattr(m, "semantic_score", None),
                    veto_reason=m.veto_reason,
                    extracted_metadata=m.extracted_metadata,
                    full_text=m.full_text,
                    markdown_text=getattr(m, "markdown_text", None),
                    user_feedback=m.user_feedback,
                    is_archived=m.is_archived,
                    created_at=m.created_at
                ) for m in models
            ]
        finally:
            db.close()

    def update_constraint(self, constraint: BusinessConstraint):
        from app.utils.logger import debug_log
        db = SessionLocal()
        committed_frequency = None
        try:
            model = db.query(ConstraintModel).first()
            if not model:
                model = ConstraintModel()
                db.add(model)
            
            model.company_name = constraint.company_name
            model.core_business = constraint.core_business
            model.qualifications = [q.model_dump() if hasattr(q, 'model_dump') else q for q in constraint.qualifications]
            model.geography_limits = [q.model_dump() if hasattr(q, 'model_dump') else q for q in constraint.geography_limits]
            model.financial_thresholds = [q.model_dump() if hasattr(q, 'model_dump') else q for q in constraint.financial_thresholds]
            model.other_constraints = [q.model_dump() if hasattr(q, 'model_dump') else q for q in constraint.other_constraints]
            model.scan_frequency = normalize_scan_frequency(constraint.scan_frequency)
            model.custom_urls = sanitize_target_urls(constraint.custom_urls or [])
            model.wechat_accounts = constraint.wechat_accounts or []
            model.updated_at = datetime.now()
            
            db.commit()
            committed_frequency = model.scan_frequency
        except Exception as e:
            db.rollback()
            debug_log(f"Error updating constraint: {e}")
        finally:
            db.close()

        # 调度器更新独立于 DB 事务，避免异常被静默吞掉
        if committed_frequency is not None:
            try:
                from app.core.scheduler import scheduler_manager
                debug_log(f"update_constraint: scheduling scan with frequency={committed_frequency}")
                scheduler_manager.schedule_scan(committed_frequency)
            except Exception as e:
                debug_log(f"Error scheduling scan after constraint update: {e}")

    def get_last_scan_at(self) -> Optional[datetime]:
        db = SessionLocal()
        try:
            model = db.query(ConstraintModel).order_by(ConstraintModel.updated_at.desc()).first()
            if not model:
                return None
            return model.last_scan_at
        finally:
            db.close()

    def mark_scan_completed(self, when: Optional[datetime] = None):
        db = SessionLocal()
        try:
            model = db.query(ConstraintModel).order_by(ConstraintModel.updated_at.desc()).first()
            if not model:
                return
            model.last_scan_at = when or datetime.now()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def add_clues(self, new_clues: List[ClueItem]):
        db = SessionLocal()
        try:
            for clue in new_clues:
                if not db.query(ClueModel).filter(ClueModel.id == clue.id).first():
                    model = ClueModel(
                        id=clue.id,
                        title=clue.title,
                        source=clue.source,
                        url=clue.url,
                        snippet=clue.snippet,
                        publish_time=clue.publish_time,
                        semantic_score=clue.semantic_score,
                        veto_reason=clue.veto_reason,
                        extracted_metadata=clue.extracted_metadata,
                        full_text=clue.full_text,
                    markdown_text=clue.markdown_text,
                    user_feedback=clue.user_feedback,
                    is_archived=clue.is_archived,
                    created_at=clue.created_at,
                    fingerprint=f"{clue.title}_{clue.source}"
                )
                    db.add(model)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error adding clues: {e}")
        finally:
            db.close()

    def subscribe_clues(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._clue_subscribers.add(queue)
        return queue

    def unsubscribe_clues(self, queue: asyncio.Queue) -> None:
        if queue in self._clue_subscribers:
            self._clue_subscribers.remove(queue)

    def publish_clue(self, clue: ClueItem) -> None:
        if not self._clue_subscribers:
            return
        payload = jsonable_encoder(clue)
        for q in list(self._clue_subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop if subscriber is too slow
                continue

    def update_clue_status(self, clue_id: str, feedback: Optional[int] = None, archived: Optional[bool] = None):
        """更新线索的反馈状态或归档状态"""
        db = SessionLocal()
        try:
            model = db.query(ClueModel).filter(ClueModel.id == clue_id).first()
            if model:
                if feedback is not None:
                    model.user_feedback = feedback
                if archived is not None:
                    model.is_archived = archived
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error updating clue status: {e}")
        finally:
            db.close()

    def save(self):
        # 数据库模型不需要手动 save，由各方法 commit 处理
        pass

state = SystemState()
