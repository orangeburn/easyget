from typing import List, Optional
from app.schemas.constraint import BusinessConstraint
from app.schemas.clue import ClueItem
from app.core.database import SessionLocal, ConstraintModel, ClueModel
from datetime import datetime

class SystemState:
    def __init__(self):
        # 内存中仅保留轻量级状态
        self.is_running: bool = False
        self.current_progress: int = 0
        self.current_step: str = "Ready"

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
                    scan_frequency=model.scan_frequency,
                    custom_urls=model.custom_urls or []
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
                    match_score=m.match_score,
                    veto_reason=m.veto_reason,
                    extracted_metadata=m.extracted_metadata,
                    full_text=m.full_text,
                    user_feedback=m.user_feedback,
                    is_archived=m.is_archived,
                    created_at=m.created_at
                ) for m in models
            ]
        finally:
            db.close()

    def update_constraint(self, constraint: BusinessConstraint):
        # ... (rest of the method remains the same)
        db = SessionLocal()
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
            model.other_constraints = constraint.other_constraints
            model.scan_frequency = constraint.scan_frequency or 30
            model.custom_urls = constraint.custom_urls or []
            model.updated_at = datetime.utcnow()
            
            db.commit()

            # 同步更新调度器
            from app.core.scheduler import scheduler_manager
            scheduler_manager.schedule_scan(model.scan_frequency)

        except Exception as e:
            db.rollback()
            print(f"Error updating constraint: {e}")
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
                        match_score=clue.match_score,
                        veto_reason=clue.veto_reason,
                        extracted_metadata=clue.extracted_metadata,
                        full_text=clue.full_text,
                        user_feedback=clue.user_feedback,
                        is_archived=clue.is_archived,
                        fingerprint=f"{clue.title}_{clue.source}"
                    )
                    db.add(model)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error adding clues: {e}")
        finally:
            db.close()

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
