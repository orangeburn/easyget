from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class ClueItem(BaseModel):
    """单条线索数据模型"""
    id: str = Field(..., description="唯一标识，通常为 URL Hash")
    source: str = Field(..., description="来源类别: 'search', 'site', 'wechat'")
    title: str = Field(..., description="招标/项目标题")
    url: str = Field(..., description="原始链接")
    snippet: Optional[str] = Field(default=None, description="摘要/正文片段")
    publish_time: Optional[datetime] = Field(default=None, description="发布时间")
    
    # 以下为后期 Analyzer 补充的内容
    extracted_metadata: Optional[dict] = Field(default=None, description="LLM结构化提取的元数据")
    semantic_score: Optional[int] = Field(default=None, description="语义匹配得分 (0-100)")
    veto_reason: Optional[str] = Field(default=None, description="一票否决原因")
    full_text: Optional[str] = Field(default=None, description="抓取到的网页正文全文")
    markdown_text: Optional[str] = Field(default=None, description="Reader 生成的 Markdown 文本")
    user_feedback: int = Field(default=0, description="用户反馈 (1: 准确, -1: 误报, 0: 未评价)")
    is_archived: bool = Field(default=False, description="是否已归档")
    
    created_at: datetime = Field(default_factory=datetime.now)
