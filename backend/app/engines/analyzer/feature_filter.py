from typing import Tuple, Optional


class StructuralFeatureScorer:
    """
    结构特征初筛：根据招标文本结构与关键词进行轻量打分，用于降噪。
    """
    def __init__(self, min_score: int = 25):
        self.min_score = min_score
        self.core_keywords = [
            "招标", "采购", "投标", "中标", "询价", "磋商", "竞争性", "比选", "遴选", "公告"
        ]
        self.field_keywords = {
            "项目编号": 8,
            "项目名称": 6,
            "预算": 10,
            "金额": 6,
            "截止": 8,
            "开标": 6,
            "联系人": 6,
            "电话": 6,
            "地址": 4,
            "采购人": 6,
            "采购代理": 6,
            "资格": 6,
            "报名": 6,
            "保证金": 6,
            "标段": 6,
            "工期": 4,
        }

    def score(self, title: str = "", snippet: str = "", full_text: str = "") -> Tuple[int, Optional[str]]:
        text = " ".join([t for t in [title, snippet, full_text] if t]).lower()
        if not text:
            return 0, "文本为空"

        score = 0
        core_hit = any(k in text for k in self.core_keywords)
        if core_hit:
            score += 20
        if title and any(k in title for k in self.core_keywords):
            score += 10

        for k, w in self.field_keywords.items():
            if k in text:
                score += w

        score = min(100, score)
        if not core_hit:
            return score, "缺少核心招标关键词"
        if score < self.min_score:
            return score, "结构特征不足"
        return score, None
