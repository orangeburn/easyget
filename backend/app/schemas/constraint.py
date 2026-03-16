from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class ConstraintItem(BaseModel):
    """单项约束条件"""
    name: str = Field(..., description="约束名称，例如：注册资本、特定资质、实施地域")
    value: str = Field(..., description="约束值，例如：500万以上、消防三级、北京市")
    is_must_have: bool = Field(default=False, description="是否为一票否决项（强约束）")


class BusinessConstraint(BaseModel):
    """
    企业/业务画像约束模型 (Business-Constraint.json)
    用于驱动搜索引擎关键词生成和线索分析器的一票否决逻辑
    """
    company_name: str = Field(..., description="企业/主体名称")
    core_business: List[str] = Field(default_factory=list, description="核心业务/产品方向")
    
    qualifications: List[ConstraintItem] = Field(
        default_factory=list, 
        description="企业具备的特定资质与资格清单"
    )
    geography_limits: List[ConstraintItem] = Field(
        default_factory=list, 
        description="地域限制（支持的实施省市区或要求本地化服务的限制）"
    )
    financial_thresholds: List[ConstraintItem] = Field(
        default_factory=list, 
        description="财务门槛（可承担的项目金额上下限、信贷能力等）"
    )
    other_constraints: List[ConstraintItem] = Field(
        default_factory=list, 
        description="其他潜在约束（如：人员规模要求、过往相似案例要求等。由提取服务补足）"
    )
    scan_frequency: int = Field(default=30, description="采集频率（分钟）")
    custom_urls: List[str] = Field(default=[], description="用户自定义的监控站点列表")
    wechat_accounts: List[str] = Field(default=[], description="微信公众号监控清单")
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_json_dict(self) -> dict:
        return self.model_dump()


class FormItem(BaseModel):
    """动态表单的单个配置项"""
    field_id: str = Field(..., description="字段的唯一标识，如 'iso9001'")
    label: str = Field(..., description="展示给用户的标签名，如 '是否拥有 ISO9001 认证'")
    field_type: str = Field(..., description="字段类型：'text', 'select', 'multiselect', 'boolean'")
    options: Optional[List[str]] = Field(default=None, description="如果类型是选择，这里为其选项列表")
    placeholder: Optional[str] = Field(default=None, description="提示占位文本")
    is_required: bool = Field(default=False, description="是否必填")


class DynamicFormSchema(BaseModel):
    """由 LLM 生成的待用户填写的动态表单结构"""
    industry_type: str = Field(..., description="LLM 识别到的行业分类")
    form_items: List[FormItem] = Field(default_factory=list, description="需要用户补充信息的表单项群")
