import json
from typing import List, Dict, Optional, Any
from app.services.llm_service import LLMService
from app.schemas.constraint import BusinessConstraint, DynamicFormSchema

class DynamicFormParser:
    """
    需求解析器：负责业务分析与画像定义。
    根据初始文档结构化基础画像，并针对其行业属性生成动态表单供用户补充细节。
    """
    def __init__(self):
        self.llm = LLMService()

    def parse_initial_document(self, document_text: str) -> BusinessConstraint:
        """
        全量解析用户提供的初始文档（如公司简介、资质列表），输出初始的结构化画像。
        """
        system_prompt = """
        你是一个专业的政企采购项目分析专家。
        请从用户提供的公司介绍或资质文档中，提取出企业特征并映射为招标约束条件。
        必须严格按照以下 JSON Schema 输出数据，不要有多余的话：

        {
            "company_name": "公司名称",
            "core_business": ["主营业务1", "主营业务2"],
            "qualifications": [{"name": "资质名称", "value": "等级或状态", "is_must_have": true}],
            "geography_limits": [{"name": "地域", "value": "要求", "is_must_have": false}],
            "financial_thresholds": [{"name": "财务项", "value": "要求", "is_must_have": false}],
            "other_constraints": []
        }
        注意：必须返回完整的对象列表，即使只有名称，也必须包含 "name", "value", "is_must_have" 三个字段。
        确保使用 UTF-8 编码，保留中文字符的原始含义。
        """
        
        result_dict = self.llm.extract_structured_data(
            system_prompt=system_prompt,
            user_input=document_text,
            response_format=None 
        )
        
        self._ensure_list_of_dicts(result_dict)
        return BusinessConstraint(**result_dict)

    def _ensure_list_of_dicts(self, data: Dict[str, Any]):
        """确保画像中的列表项都是字典而非原始字符串"""
        list_fields = ["qualifications", "geography_limits", "financial_thresholds", "other_constraints"]
        for field in list_fields:
            if field in data and isinstance(data[field], list):
                new_list = []
                for item in data[field]:
                    if isinstance(item, str):
                        new_list.append({"name": item, "value": "已具备", "is_must_have": False})
                    elif isinstance(item, dict):
                        new_list.append(item)
                data[field] = new_list

    def generate_dynamic_form(self, current_constraint: BusinessConstraint) -> DynamicFormSchema:
        """
        分析当前画像所处的行业，推测其投标所需的高频且关键的隐形条件，生成一个动态表单。
        表单支持选项、多选、文本输入等。
        """
        system_prompt = f"""
        你精通招标采购规则。考虑到企业目前的状况（JSON格式如下）：
        {current_constraint.model_dump_json()}
        
        任务：
        请分析该企业所在行业的招投标特点。思考在他们投标中，有哪些高频资质或隐约门槛是他们尚未提供的？
        （例如：信创行业是否有涉密资质、建筑行业是否有安全生产许可证、餐饮行业是否有卫生许可）。
        请生成一个表单，供用户补充这些缺失的信息。
        
        输出格式必须为 JSON，结构如下：
        {{
            "industry_type": "识别到的行业名称",
            "form_items": [
                {{
                    "field_id": "字段英文唯一标识",
                    "label": "表单项标题",
                    "field_type": "select | multiselect | text | boolean",
                    "options": ["选项1", "选项2"], // 如果是 text 或 boolean 则可为 null
                    "placeholder": "请输入...",
                    "is_required": false
                }}
            ]
        }}
        """
        
        result_dict = self.llm.extract_structured_data(
            system_prompt=system_prompt,
            user_input="请输出生成表单的完整 JSON",
            response_format=None
        )
        
        return DynamicFormSchema(**result_dict)

    def update_constraint_from_form(self, current_constraint: BusinessConstraint, form_data: Dict[str, Any]) -> BusinessConstraint:
        """
        将用户填写的表单结果融合到原有业务画像中。
        """
        system_prompt = f"""
        原有企业画像如下：
        {current_constraint.model_dump_json()}
        
        用户在补充表单中填写了新的信息：
        {json.dumps(form_data, ensure_ascii=False)}
        
        请将新信息融合进画像中，梳理并分类到对应的 qualifications， geography_limits, financial_thresholds 或 other_constraints 中。
        注意：每个列表项必须是包含 "name", "value", "is_must_have" 的完整对象。严禁直接使用字符串。
        返回更新后的完整企业画像 JSON，结构与初始阶段提取的内容保持一致。
        """
        
        result_dict = self.llm.extract_structured_data(
            system_prompt=system_prompt,
            user_input="请整合新信息并输出完整的 JSON 画像",
            response_format=None
        )
        
        self._ensure_list_of_dicts(result_dict)
        return BusinessConstraint(**result_dict)

    def generate_keywords(self, constraint: BusinessConstraint) -> List[str]:
        """
        基于完整的企业画像，生成用于招标搜索的高质量关键词。
        """
        system_prompt = f"""
        你是政府采购与招标信息检索专家。我需要你根据我的公司介绍，为我生成我司业务范围内的关键词，用于在搜索引擎搜索招标信息。

        **生成要求：**
        1. 关键词必须聚焦公司主营业务、核心产品或服务，使用行业标准术语。
        2. 每条关键词必须包含“招标/采购/招标公告/采购公告/中标结果/询价/竞争性磋商”中的至少一个。
        3. 只输出用于搜索引擎检索的关键词，不要输出任何解释。
        4. 输出 8-16 条关键词，覆盖核心业务与主要资质方向。

        **严禁包含：**
        - 任何关于 Easyget 软件功能的词（如：获取、过滤、评估、分析、同步、导出）。
        - 任何系统架构或技术实现词汇（如：Agent、代理、爬虫、自动化、LLM、提取）。
        - 描述采集过程的动词。

        **输出格式：**
        请直接返回一个纯 JSON 数组字符串。

        企业画像：
        {constraint.model_dump_json()}
        """
        
        result_list = self.llm.extract_structured_data(
            system_prompt=system_prompt,
            user_input="请输出搜索关键词数组",
            response_format=None
        )
        
        return result_list if isinstance(result_list, list) else []
