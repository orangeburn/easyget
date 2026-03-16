import asyncio
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.analyzer.feature_filter import StructuralFeatureScorer

class CluePipeline:
    """
    极简版分析流水线：仅做去重和基于关键词的结构特征筛除，不再调用 LLM 抽取全文。
    """
    def __init__(self):
        self.feature_scorer = StructuralFeatureScorer()

    async def _process_single_clue(self, clue: ClueItem) -> ClueItem:
        # 1. 结构特征初筛（降噪）
        feature_score, feature_reason = self.feature_scorer.score(
            title=clue.title or "",
            snippet=clue.snippet or "",
            full_text="" # 不再耗时抓取全文
        )
        if feature_reason:
            clue.match_score = 0
            clue.veto_reason = f"{feature_reason}({feature_score})"
        else:
            clue.match_score = feature_score
            
        return clue

    async def run(self, raw_clues: List[ClueItem], constraint: BusinessConstraint) -> List[ClueItem]:
        from app.core.database import SessionLocal, ClueModel
        from difflib import SequenceMatcher

        def is_similar(a: str, b: str) -> bool:
            return SequenceMatcher(None, a, b).ratio() > 0.85

        # 1. 基础去重与数据库比对
        db = SessionLocal()
        try:
            # 获取最近的线索指纹用于快速比对
            existing_clues = db.query(ClueModel).order_by(ClueModel.created_at.desc()).limit(200).all()
            
            unique_clues = []
            for raw in raw_clues:
                is_duplicate = False
                for existing in existing_clues:
                    # 语义级别判断：标题极其相似且来源一致，或内容极其相似
                    if is_similar(raw.title, existing.title) or (raw.snippet and is_similar(raw.snippet, existing.snippet)):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_clues.append(raw)
        finally:
            db.close()
        
        if not unique_clues:
            return []

        # 2. 并发通过轻量流水线
        sem = asyncio.Semaphore(10)
        
        async def bounded_process(item: ClueItem):
            async with sem:
                return await self._process_single_clue(item)
                
        processed = await asyncio.gather(*(bounded_process(c) for c in unique_clues))
        
        # 排序：有 veto 理由的沉底，剩下的按 match_score 倒序
        sorted_clues = sorted(processed, key=lambda c: (c.veto_reason is None, c.match_score or 0), reverse=True)
        return sorted_clues
