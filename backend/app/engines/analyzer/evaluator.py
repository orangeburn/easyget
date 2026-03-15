from typing import Tuple, Optional
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint

class ClueEvaluator:
    """
    负责基于提取出的元数据，结合企业画像，执行“一票否决”与“加权打分”逻辑
    """
    def __init__(self):
        # 简单权重配置，实际业务可抽离至配置文件或数据库
        self.weights = {
            "business_match": 40,
            "qualification_match": 40,
            "location_match": 20
        }

    def evaluate(self, clue: ClueItem, constraint: BusinessConstraint) -> Tuple[int, Optional[str]]:
        """
        :return: (最终得分 0-100, 一票否决的原因(如有))
        """
        meta = clue.extracted_metadata
        if not meta:
            return (0, "无法提取结构化元数据")
            
        score = 0
        veto_reason = None
        
        # 1. 核心业务否决校验
        # 1. 核心业务评分
        # 从 LLM 提取的元数据中获取匹配结果。如果缺失（由于提取失败或旧数据），默认认为匹配（不扣分），
        # 但如果显式标记为 False，则认为不完全匹配主营业务，不加业务匹配分。
        if meta.get("is_matched_core_business", True):
            score += self.weights["business_match"]
            
        # 2. 强资质 (Must Have) 一票否决校验
        required_by_project = meta.get("required_qualifications", [])
        my_qualifications_dict = {q.name: q.value for q in constraint.qualifications}
        
        for req_q in required_by_project:
            # 判断招标方要求的是否在我方缺失名单（这里简单实现名称比对，实际建议上 LLM 语义相似度）
            found = False
            for my_name in my_qualifications_dict.keys():
                if req_q in my_name or my_name in req_q:
                    found = True
                    break
            
            # 如果没找到，且没有其他变通条件，如果画像里认为资质是必备壁垒（简化逻辑）
            if not found:
                veto_reason = f"缺失关键强制资质要求：{req_q}"
                return (0, veto_reason)
                
        # 满分通过资质考核
        score += self.weights["qualification_match"]

        # 3. 预算/地理等门槛核验
        location = meta.get("location")
        if location:
            my_geo = [g.value for g in constraint.geography_limits]
            if my_geo:
                match_geo = any(g in location or location in g for g in my_geo)
                if match_geo:
                    score += self.weights["location_match"]
                else:
                    veto_reason = f"实施地域不在服务范围内：{location}"
                    return (0, veto_reason)
            else:
                score += self.weights["location_match"]
        else:
            # 没提地点，默认给分
            score += self.weights["location_match"]
            
        return (score, veto_reason)
