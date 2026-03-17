import asyncio
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint

class CluePipeline:
    """
    语义驱动的分析流水线：利用 LLM 进行语义过滤，不再进行硬编码的规则打分。
    """
    def __init__(self):
        pass

    async def _process_single_clue(self, clue: ClueItem, constraint: BusinessConstraint = None) -> ClueItem:
        from app.engines.analyzer.llm_filter import llm_filter
        from app.engines.analyzer.feature_filter import StructuralFeatureScorer
        
        # 0. 结构化硬过滤（地域/金额/时间）
        if constraint:
            scorer = StructuralFeatureScorer(min_score=0)
            _, veto_reason = scorer.score(
                title=clue.title or "",
                snippet=clue.snippet or "",
                full_text=clue.full_text or "",
                constraint=constraint,
                publish_time=clue.publish_time
            )
            if veto_reason and (
                veto_reason.startswith("非目标地域")
                or veto_reason.startswith("项目规模过小")
                or veto_reason.startswith("发布时间超过")
            ):
                clue.veto_reason = veto_reason
                return clue

        # 1. 语义过滤（调用 LLM）
        is_lead, reason, category = await llm_filter.filter(
            title=clue.title or ""
        )
        
        # 2. 填充元数据
        if not clue.extracted_metadata:
            clue.extracted_metadata = {}
        clue.extracted_metadata["category"] = category
        clue.extracted_metadata["analysis_reason"] = reason

        if not is_lead:
            clue.veto_reason = reason # 如：行业新闻、无关广告等
        else:
            clue.veto_reason = None
            
        return clue

    async def run(self, raw_clues: List[ClueItem], constraint: BusinessConstraint) -> List[ClueItem]:
        from app.core.database import SessionLocal, ClueModel
        from difflib import SequenceMatcher

        def is_similar(a: str, b: str) -> bool:
            return SequenceMatcher(None, a, b).ratio() > 0.85

        # 1. 基础去重与数据库比对
        db = SessionLocal()
        processed_raw_clues = []
        try:
            # 获取最近的线索指纹用于快速比对
            existing_clues = db.query(ClueModel).order_by(ClueModel.created_at.desc()).limit(200).all()
            
            for raw in raw_clues:
                is_duplicate = False
                for existing in existing_clues:
                    # 语义级别判断：标题极其相似且来源一致，或内容极其相似
                    if is_similar(raw.title, existing.title) or (raw.snippet and is_similar(raw.snippet, existing.snippet)):
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    raw.veto_reason = "内容重复"
                
                processed_raw_clues.append(raw)
        finally:
            db.close()
        
        if not processed_raw_clues:
            return []

        # 2. 并发通过轻量流水线 (仅针对非重复项进行特征打分，节省资源)
        sem = asyncio.Semaphore(10)
        
        async def bounded_process(item: ClueItem):
            if item.veto_reason == "内容重复":
                try:
                    from app.core.state import state
                    state.publish_clue(item)
                except Exception:
                    pass
                return item
            async with sem:
                processed = await self._process_single_clue(item, constraint)
                try:
                    from app.core.state import state
                    state.publish_clue(processed)
                except Exception:
                    pass
                return processed
                
        processed = await asyncio.gather(*(bounded_process(c) for c in processed_raw_clues))
        
        # 排序：有 veto 理由的沉底，其余保持原始相对顺序
        sorted_clues = sorted(processed, key=lambda c: (c.veto_reason is None), reverse=True)
        return sorted_clues

    async def run_stream(self, clue_queue: asyncio.Queue, done_event: asyncio.Event, constraint: BusinessConstraint):
        """流式处理：每条线索完成 LLM 过滤后立即发布并落库。"""
        from app.core.database import SessionLocal, ClueModel
        from difflib import SequenceMatcher
        from app.core.state import state

        def is_similar(a: str, b: str) -> bool:
            return SequenceMatcher(None, a, b).ratio() > 0.85

        # 预加载最近的线索用于去重
        db = SessionLocal()
        try:
            existing_clues = db.query(ClueModel).order_by(ClueModel.created_at.desc()).limit(200).all()
        finally:
            db.close()

        sem = asyncio.Semaphore(10)

        async def process_one(item: ClueItem):
            # 1) 去重（仅对比历史库）
            is_duplicate = False
            for existing in existing_clues:
                if is_similar(item.title, existing.title) or (item.snippet and is_similar(item.snippet, existing.snippet)):
                    is_duplicate = True
                    break
            if is_duplicate:
                item.veto_reason = "内容重复"
                state.publish_clue(item)
                state.add_clues([item])
                return

            # 2) LLM 过滤
            async with sem:
                processed = await self._process_single_clue(item, constraint)
            state.publish_clue(processed)
            state.add_clues([processed])

        async def worker():
            while True:
                if done_event.is_set() and clue_queue.empty():
                    break
                try:
                    item = await asyncio.wait_for(clue_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                try:
                    await process_one(item)
                finally:
                    clue_queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(4)]
        await asyncio.gather(*workers)
