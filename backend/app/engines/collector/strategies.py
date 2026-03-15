import httpx
import uuid
import abc
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.core.config import settings

from app.engines.collector.base import BaseCollectorStrategy

class GeneralSearchStrategy(BaseCollectorStrategy):
    """
    全网搜索模式：集成 Serper.dev (Google Search API) 实现。
    通过画像自动构建搜索指令，并解析返回的网页摘要。
    """
    def __init__(self):
        self.api_url = "https://google.serper.dev/search"
        self.api_key = settings.SEARCH_API_KEY

    def _build_query(self, constraint: BusinessConstraint) -> str:
        """根据画像构建高级搜索指令"""
        core = constraint.core_business[0] if constraint.core_business else ""
        company = constraint.company_name
        
        # 典型的招标关键词组合
        # site:*.gov.cn 过滤政府招标，site:*.edu.cn 过滤高校
        query = f'"{core}" 招标公告 (site:*.gov.cn OR site:*.com.cn)'
        
        if constraint.geography_limits:
            loc = constraint.geography_limits[0].value
            query = f"{loc} {query}"
            
        return query

    async def _search_single_keyword(self, client: httpx.AsyncClient, keyword: str) -> List[ClueItem]:
        """执行单个关键词的搜索"""
        print(f"[GeneralSearch] 正在搜索: {keyword}...")
        payload = {
            "q": keyword,
            "gl": "cn",
            "hl": "zh-cn",
            "autocorrect": True
        }
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = await client.post(self.api_url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            organic = data.get("organic", [])
            for item in organic:
                results.append(ClueItem(
                    id=str(uuid.uuid4()),
                    source="search",
                    title=item.get("title", "无标题"),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    publish_time=datetime.now()
                ))
            print(f"[GeneralSearch] 完成: {keyword} | 命中: {len(results)}")
            return results
        except Exception as e:
            print(f"[GeneralSearch] 关键词 [{keyword}] 采集失败: {e}")
            return []

    async def collect(self, constraint: BusinessConstraint, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        
        # 1. 解析关键词列表
        keywords = []
        if search_keywords_str:
            # 支持逗号、中英文顿号、空格分隔
            import re
            keywords = [k.strip() for k in re.split(r'[,，、\s]+', search_keywords_str) if k.strip()]
        
        # 如果没有关键词，则使用默认的兜底 query
        if not keywords:
            keywords = [self._build_query(constraint)]

        if not self.api_key or self.api_key == "your_search_api_key_here":
            print("[GeneralSearch] 未检测到有效的 SEARCH_API_KEY，切换至 [浏览器搜索模式]...")
            from app.engines.collector.browser_search_strategy import BrowserSearchStrategy
            browser_strategy = BrowserSearchStrategy()
            return await browser_strategy.collect(constraint, **kwargs)

        print(f"[GeneralSearch] 开始并发采集，共 {len(keywords)} 个关键词")
        
        async with httpx.AsyncClient() as client:
            tasks = [self._search_single_keyword(client, kw) for kw in keywords]
            results_groups = await asyncio.gather(*tasks)
            
            # 2. 汇总并根据 URL 去重
            all_results = []
            seen_urls = set()
            for group in results_groups:
                for item in group:
                    if item.url not in seen_urls:
                        all_results.append(item)
                        seen_urls.add(item.url)
            
            print(f"[GeneralSearch] 并发采集结束，去重后共 {len(all_results)} 条原始线索")
            return all_results

    def _mock_data(self, constraint: BusinessConstraint) -> List[ClueItem]:
        return [
            ClueItem(
                id=str(uuid.uuid4()),
                source="search",
                title=f"关于采购【{constraint.core_business[0] if constraint.core_business else '相关业务'}】的公开招标公告",
                url="https://example.com/bidding/1001",
                snippet="本项目要求供应商必须提供合格的资质...",
                publish_time=datetime.now()
            )
        ]
