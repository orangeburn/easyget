import json
from typing import Dict, Any, List
from openai import OpenAI
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model_name = settings.MODEL_NAME
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=30.0)

    def _get_common_params(self, temperature: float = 0.7) -> Dict[str, Any]:
        """获取通用请求参数，自动适配 MiniMax 特性"""
        params = {
            "model": self.model_name,
            "temperature": temperature,
        }
        # 仅当 Base URL 包含 minimax 时才启用特有参数，确保对 OpenAI/DeepSeek 的兼容性
        if self.base_url and "minimax" in self.base_url.lower():
            params["extra_body"] = {"reasoning_split": True}
        return params

    def generate_chat_response(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        """基础对话请求"""
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self.client.chat.completions.create(
            messages=formatted_messages,
            **self._get_common_params(temperature=0.7)
        )
        return response.choices[0].message.content

    def extract_structured_data(self, system_prompt: str, user_input: str, response_format: Any) -> Any:
        """提取结构化数据（并清理可能的思考块或 Markdown 标记）"""
        import re
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        response = self.client.chat.completions.create(
            messages=messages,
            response_format={"type": "json_object"},
            **self._get_common_params(temperature=0.1)
        )
        content = response.choices[0].message.content
        
        # 清理内容：移除微信/MiniMax 等模型可能附带的 <think> 块或 Markdown 语法
        # 1. 移除 <think>...</think>
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # 2. 提取 JSON 代码块 (```json ... ``` 或 ``` ... ```)
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, flags=re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        # 3. 极其脆弱的清理：如果还是不行，尝试寻找第一个 { 和最后一个 }
        if not content.strip().startswith(('{', '[')):
            fuzzy_match = re.search(r'(\{.*\}|\[.*\])', content, flags=re.DOTALL)
            if fuzzy_match:
                content = fuzzy_match.group(1)
                
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            from app.utils.logger import debug_log
            debug_log(f"LLMService: Failed to parse JSON. Content: {content[:200]}... Error: {e}")
            raise e
