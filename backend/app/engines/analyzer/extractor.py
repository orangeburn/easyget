from typing import List, Dict, Any, Optional
from app.services.llm_service import LLMService
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
import asyncio
from pydantic import BaseModel, ConfigDict, StrictStr, StrictBool, ValidationError


class ExtractedMetadataSchema(BaseModel):
    budget: StrictStr
    location: StrictStr
    deadline: StrictStr
    requirements: StrictStr
    is_matched_core_business: StrictBool
    summary: StrictStr

    model_config = ConfigDict(extra="ignore")

class DeepContentExtractor:
    """
    深度内容提取器：负责从原始网页文本中提取核心招标信息。
    """
    def __init__(self):
        self.llm = LLMService()

    async def extract(self, full_text: str, constraint: BusinessConstraint) -> Dict[str, Any]:
        """
        利用 LLM 从全文中提取画像关注的关键字段。
        """
        if not full_text or len(full_text) < 50:
            return {}

        system_prompt = """
你是专业的招标信息分析助手。正文为 Markdown 格式。
请从正文中提取以下 JSON 核心元数据，不要包含任何 Markdown 格式或解释性文字：
{
  "budget": "预算金额（含单位，如 500万元，未知则留空）",
  "location": "实施地点（具体到省市）",
  "deadline": "投标/响应截止日期",
  "requirements": "核心资质准入门槛（简述）",
  "is_matched_core_business": "布尔值：此招标是否属于该企业的主营业务范围",
  "summary": "一句总结招标内容（30字内）"
}
"""
        # 构建更丰富的上下文
        biz_context = f"公司: {constraint.company_name}\n主营业务: {', '.join(constraint.core_business)}\n"
        if constraint.qualifications:
            biz_context += "具备资质: " + ", ".join([f"{q.name}({q.value})" for q in constraint.qualifications]) + "\n"
            
        user_input = f"企业上下文：\n{biz_context}\n\n待分析招标正文（Markdown）：\n{full_text[:3000]}"
        
        try:
            # 使用 LLM 进行结构化提取
            # 这里复用 LLMService 的 extract_structured_data
            result = self.llm.extract_structured_data(system_prompt, user_input, response_format=None)
            if not isinstance(result, dict):
                return {}
            validated = ExtractedMetadataSchema.model_validate(result)
            return validated.model_dump()
        except ValidationError as e:
            print(f"[DeepContentExtractor] 输出校验失败: {e}")
            return {}
        except Exception as e:
            print(f"[DeepContentExtractor] 提取失败: {e}")
            return {}

deep_extractor = DeepContentExtractor()
