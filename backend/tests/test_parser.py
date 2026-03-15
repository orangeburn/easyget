import pytest
from app.schemas.constraint import BusinessConstraint, ConstraintItem, DynamicFormSchema
from app.engines.parser import DynamicFormParser
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_dynamic_parser():
    parser = DynamicFormParser()
    parser.llm.client = MagicMock()
    return parser

def test_parse_initial_document(mock_dynamic_parser):
    """测试从文本提取结构化企业约束"""
    doc_text = "我们是北京华信科技有限公司，主营软件开发，拥有CMMI 3级资质，只做北京本地项目。"
    
    mock_response = {
        "company_name": "北京华信科技有限公司",
        "core_business": ["软件开发"],
        "qualifications": [{"name": "CMMI等级", "value": "3级", "is_must_have": True}],
        "geography_limits": [{"name": "实施地域", "value": "北京本地", "is_must_have": True}],
        "financial_thresholds": [],
        "other_constraints": []
    }
    
    with patch.object(mock_dynamic_parser.llm, 'extract_structured_data', return_value=mock_response):
        constraint = mock_dynamic_parser.parse_initial_document(doc_text)
        
        assert isinstance(constraint, BusinessConstraint)
        assert constraint.company_name == "北京华信科技有限公司"
        assert len(constraint.core_business) == 1
        assert constraint.qualifications[0].name == "CMMI等级"

def test_generate_dynamic_form(mock_dynamic_parser):
    """测试基于画像行业推断生成动态表单结构"""
    constraint = BusinessConstraint(
        company_name="测试工程公司",
        core_business=["建筑施工"],
        qualifications=[],
        geography_limits=[],
        financial_thresholds=[],
        other_constraints=[]
    )
    
    mock_response = {
        "industry_type": "建筑行业",
        "form_items": [
            {
                "field_id": "safety_license",
                "label": "是否具备安全生产许可证",
                "field_type": "boolean",
                "options": None,
                "placeholder": None,
                "is_required": True
            }
        ]
    }
    
    with patch.object(mock_dynamic_parser.llm, 'extract_structured_data', return_value=mock_response) as mock_llm:
        form_schema = mock_dynamic_parser.generate_dynamic_form(constraint)
        
        assert isinstance(form_schema, DynamicFormSchema)
        assert form_schema.industry_type == "建筑行业"
        assert form_schema.form_items[0].field_id == "safety_license"
        
        call_args = mock_llm.call_args[1]
        assert "测试工程公司" in call_args['system_prompt']

def test_update_constraint_from_form(mock_dynamic_parser):
    """测试将用户提交的动态表单数据合并入基础约束模型"""
    constraint = BusinessConstraint(company_name="基础公司", core_business=[], qualifications=[], geography_limits=[], financial_thresholds=[], other_constraints=[])
    form_data = {"safety_license": True, "iso_level": "ISO9001"}
    
    mock_response = {
        "company_name": "基础公司",
        "core_business": [],
        "qualifications": [
            {"name": "安全生产许可", "value": "是", "is_must_have": True},
            {"name": "ISO认证", "value": "ISO9001", "is_must_have": False}
        ],
        "geography_limits": [],
        "financial_thresholds": [],
        "other_constraints": []
    }
    
    with patch.object(mock_dynamic_parser.llm, 'extract_structured_data', return_value=mock_response):
        res = mock_dynamic_parser.update_constraint_from_form(constraint, form_data)
        assert len(res.qualifications) == 2
        assert res.qualifications[0].name == "安全生产许可"
