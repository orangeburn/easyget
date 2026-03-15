import json
from typing import Dict, Any, List
from openai import OpenAI
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model_name = settings.MODEL_NAME
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_chat_response(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        """基础对话请求"""
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=formatted_messages,
            temperature=0.7
        )
        return response.choices[0].message.content

    def extract_structured_data(self, system_prompt: str, user_input: str, response_format: Any) -> Any:
        """提取结构化数据（利用 OpenAI JSON mode 或 function calling）"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        content = response.choices[0].message.content
        return json.loads(content)
