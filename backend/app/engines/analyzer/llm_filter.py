import json
from typing import Optional, Tuple
from app.services.llm_service import LLMService
from app.utils.logger import debug_log

class LLMSemanticFilter:
    """
    语义过滤器：利用 LLM 判定内容是否为有效的“招标/采购/项目机会”线索。
    """
    def __init__(self):
        self.llm = LLMService()

    async def filter(self, title: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        返回 (is_lead, reason, category)
        """
        system_prompt = """
你是专业的政企采购项目分析助手。你的任务是判断给出的“标题”是否为一个具体的“招标公告”、“采购预告”、“中标结果”或“项目机会”。

**必须排除（标记为 is_lead: false）**：
1. 行业新闻、政策解读、市场动态、评论文章。
2. 企业宣传、品牌公关、广告、招聘信息。
3. 纯粹的学术报告、技术交流、会议通知。
4. 任何不包含明确“采购主体”和“采购标的”的资讯。

**判断标准**：
- 如果涉及具体的金钱交易、服务外包、设备采购、工程招标，且具有时效性，标记为 is_lead: true。
- 否则一律标记为 false。

请返回 JSON 格式：
{
  "is_lead": bool,
  "category": "正式招标" | "采购意向" | "中标公示" | "行业新闻" | "企业招聘" | "其他非项目",
  "reason": "简述判断理由"
}
"""
        user_input = f"标题: {title}"
        
        try:
            # 使用 extract_structured_data 确保返回 JSON
            result = self.llm.extract_structured_data(
                system_prompt=system_prompt,
                user_input=user_input,
                response_format=None
            )
            
            is_lead = result.get("is_lead", False)
            reason = result.get("reason", "Unknown")
            category = result.get("category", "其他")
            
            if is_lead:
                return True, reason, category
            return False, reason, category
        except Exception as e:
            debug_log(f"LLMSemanticFilter: Filter failed - {e}")
            # 容错处理：如果 AI 挂了，默认通过（由人工进一步筛选）以防漏掉线索
            return True, "AI解析失败(默认通过)", "待分类"

llm_filter = LLMSemanticFilter()
