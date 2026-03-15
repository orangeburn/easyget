import asyncio
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.analyzer.extractor import deep_extractor
from app.engines.analyzer.evaluator import ClueEvaluator
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

class CluePipeline:
    """
    负责将收集到的原始 Clue 序列经过流水线处理（提取 -> 查重 -> 评分）。
    """
    def __init__(self):
        self.evaluator = ClueEvaluator()

    async def _process_single_clue(self, clue: ClueItem, constraint: BusinessConstraint) -> ClueItem:
        """对单条线索进行深度处理：抓取原文 -> 结构化分析 -> 评分"""
        
        # 1. 抓取全文（如果缺失）
        if not clue.full_text and clue.url.startswith("http"):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await stealth_async(page)
                    await page.goto(clue.url, timeout=20000, wait_until="domcontentloaded")
                    clue.full_text = await page.evaluate("() => document.body.innerText")
                    await browser.close()
            except Exception as e:
                print(f"[Pipeline] 抓取全文失败 {clue.url}: {e}")

        # 2. 深度结构化提取
        if clue.full_text:
            deep_meta = await deep_extractor.extract(clue.full_text, constraint)
            if deep_meta:
                if not clue.extracted_metadata:
                    clue.extracted_metadata = {}
                clue.extracted_metadata.update(deep_meta)
        
        # 3. 定制化打分
        try:
            score, veto_reason = self.evaluator.evaluate(clue, constraint)
            clue.match_score = score
            clue.veto_reason = veto_reason
        except Exception as e:
            print(f"[Pipeline] 评分异常: {e}")
            clue.match_score = 0
            
        return clue

    async def run(self, raw_clues: List[ClueItem], constraint: BusinessConstraint) -> List[ClueItem]:
        """异步批量执行分析流水线。在单机极简版中直接通过异步控制并发度。"""
        from app.core.database import SessionLocal, ClueModel
        from difflib import SequenceMatcher

        def is_similar(a: str, b: str) -> bool:
            return SequenceMatcher(None, a, b).ratio() > 0.85

        # 1. 基础去重与数据库比对
        db = SessionLocal()
        try:
            # 获取最近的线索指纹用于快速比对
            existing_clues = db.query(ClueModel).order_by(ClueModel.created_at.desc()).limit(100).all()
            
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

        # 2. 并发通过 LLM 流水线（注意控制并发以防过载，可使用 semaphore）
        sem = asyncio.Semaphore(5)
        
        async def bounded_process(item: ClueItem):
            async with sem:
                return await self._process_single_clue(item, constraint)
                
        processed = await asyncio.gather(*(bounded_process(c) for c in unique_clues))
        
        # 排序：有 veto 理由的沉底且得分为 0，剩下的按 match_score 倒序
        sorted_clues = sorted(processed, key=lambda c: (c.veto_reason is None, c.match_score or 0), reverse=True)
        return sorted_clues
