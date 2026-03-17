import re
from datetime import datetime, timedelta
from typing import Tuple, Optional
from app.schemas.constraint import BusinessConstraint


class StructuralFeatureScorer:
    """
    结构特征初筛：根据招标文本结构与关键词进行轻量打分，并执行地域与金额过滤。
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

    def score(self, title: str = "", snippet: str = "", full_text: str = "", 
              constraint: BusinessConstraint = None, publish_time: Optional[datetime] = None) -> Tuple[int, Optional[str]]:
        text = " ".join([t for t in [title, snippet, full_text] if t]).lower()
        if not text:
            return 0, "文本为空"

        # 1. 地域过滤
        if constraint and constraint.geography_limits:
            region_limit = constraint.geography_limits[0].value
            if region_limit != "全国":
                # 支持 "省-市" 格式，只要命中其中之一即可（通常城市更精准）
                parts = region_limit.split('-')
                if not any(p in text for p in parts):
                    return 0, f"非目标地域({region_limit})"

        # 2. 金额过滤 (项目规模)
        if constraint and constraint.financial_thresholds:
            try:
                min_amount = float(constraint.financial_thresholds[0].value)
                # 尝试从文本中提取金额 (支持 万, 亿, 元)
                amount_match = re.search(r'(?:预算|金额|合计|价格).*?([\d\.]+)\s*(万|亿|元)', text)
                if amount_match:
                    val = float(amount_match.group(1))
                    unit = amount_match.group(2)
                    if unit == '亿': val *= 10000
                    elif unit == '元': val /= 10000
                    
                    if val < min_amount:
                        return 0, f"项目规模过小({val}万 < {min_amount}万)"
            except ValueError:
                pass

        # 3. 发布时间过滤
        if constraint and constraint.other_constraints:
            time_limit_item = next((c for c in constraint.other_constraints if c.name == "发布时间"), None)
            if time_limit_item:
                if not publish_time:
                    return 0, "缺少发布时间"
                limit = time_limit_item.value # 3d, 1w, 1m
                now = datetime.now()
                if limit == "3d" and publish_time < now - timedelta(days=3):
                    return 0, "发布时间超过三天"
                elif limit == "1w" and publish_time < now - timedelta(days=7):
                    return 0, "发布时间超过一周"
                elif limit == "1m" and publish_time < now - timedelta(days=30):
                    return 0, "发布时间超过一月"

        final_score = 0
        core_hit = any(k in text for k in self.core_keywords)
        if core_hit:
            final_score += 20
        if title and any(k in title for k in self.core_keywords):
            final_score += 10

        for k, w in self.field_keywords.items():
            if k in text:
                final_score += w

        final_score = min(100, final_score)
        if not core_hit:
            return final_score, "缺少核心招标关键词"
        if final_score < self.min_score:
            return final_score, "结构特征不足"
        return final_score, None
