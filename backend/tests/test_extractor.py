import pytest
from unittest.mock import patch

from app.engines.analyzer.extractor import DeepContentExtractor
from app.schemas.constraint import BusinessConstraint


@pytest.mark.asyncio
async def test_extractor_markdown_and_schema_valid():
    extractor = DeepContentExtractor()
    constraint = BusinessConstraint(
        company_name="理想国际",
        core_business=["建筑工程"],
        qualifications=[],
        geography_limits=[],
    )
    markdown = (
        "# 招标公告\n"
        "- 预算：500万元\n"
        "- 地点：广东省广州市\n"
        "- 截止日期：2026-03-20\n"
        "本项目为市政道路改造工程，包含土建、管线迁改与交通疏解。\n"
        "要求具备建筑施工总承包二级及以上资质。"
    )

    with patch.object(extractor.llm, "extract_structured_data") as mock_extract:
        mock_extract.return_value = {
            "budget": "500万元",
            "location": "广东省广州市",
            "deadline": "2026-03-20",
            "requirements": "建筑施工总承包二级",
            "is_matched_core_business": True,
            "summary": "广州市建筑工程项目招标"
        }
        result = await extractor.extract(markdown, constraint)

    assert result["budget"] == "500万元"
    assert result["is_matched_core_business"] is True
    called_user_input = mock_extract.call_args[0][1]
    assert "待分析招标正文（Markdown）" in called_user_input
    assert "# 招标公告" in called_user_input


@pytest.mark.asyncio
async def test_extractor_schema_invalid_returns_empty():
    extractor = DeepContentExtractor()
    constraint = BusinessConstraint(
        company_name="理想国际",
        core_business=["建筑工程"],
        qualifications=[],
        geography_limits=[],
    )
    markdown = (
        "# 招标公告\n"
        "- 预算：500万元\n"
        "- 地点：广东省广州市\n"
        "- 截止日期：2026-03-20\n"
        "本项目为市政道路改造工程，包含土建、管线迁改与交通疏解。\n"
        "要求具备建筑施工总承包二级及以上资质。"
    )

    with patch.object(extractor.llm, "extract_structured_data") as mock_extract:
        mock_extract.return_value = {
            "budget": 500,
            "location": "广东省广州市",
            "deadline": "2026-03-20",
            "requirements": "建筑施工总承包二级",
            "is_matched_core_business": "yes",
            "summary": "广州市建筑工程项目招标"
        }
        result = await extractor.extract(markdown, constraint)

    assert result == {}
