from typing import List, Optional
from pydantic import BaseModel, Field

class LLMQueryResponse(BaseModel):
    """基础的LLM响应载体"""
    content: str = Field(..., description="LLM的正文回复")
    extracted_entities: Optional[List[dict]] = Field(default=None, description="结构化提取的实体")
