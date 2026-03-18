import httpx
import asyncio
import uuid
import abc
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.core.config import settings
from app.utils.keywords import split_search_keywords

from app.engines.collector.base import BaseCollectorStrategy

def _extract_date_from_text(text: str) -> Optional[datetime]:
    """Try to parse publish date from snippet text. Return None if unknown."""
    if not text:
        return None
    if "天前" in text:
        match = re.search(r'(\d+)天前', text)
        if match:
            return datetime.now() - timedelta(days=int(match.group(1)))
    if "小时前" in text:
        match = re.search(r'(\d+)小时前', text)
        if match:
            return datetime.now() - timedelta(hours=int(match.group(1)))

    patterns = [
        r'(\d{4}-\d{1,2}-\d{1,2})',
        r'(\d{4}年\d{1,2}月\d{1,2}日)',
        r'(\d{4}/\d{1,2}/\d{1,2})'
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            date_str = match.group(1)
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('/', '-')
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                continue
    return None

class TavilySearchStrategy(BaseCollectorStrategy):
    """
    Tavily AI 搜索模式：针对 AI Agent 优化的搜索引擎。
    """
    def __init__(self):
        self.api_url = "https://api.tavily.com/search"

    async def collect(self, constraint: BusinessConstraint, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        on_clue = kwargs.get("on_clue")
        api_key = settings.TAVILY_API_KEY if settings.TAVILY_API_ENABLED else None
        if not api_key or not search_keywords_str:
            return []

        keywords = split_search_keywords(search_keywords_str)
        
        all_results = []
        async with httpx.AsyncClient() as client:
            for kw in keywords:
                try:
                    from app.core.state import state
                    if state.is_paused:
                        break
                except Exception:
                    pass
                payload = {
                    "api_key": api_key,
                    "query": kw,
                    "search_depth": "advanced",
                    "include_answer": False,
                    "include_images": False,
                    "max_results": 10
                }
                try:
                    print(f"[TavilySearch] 正在搜索: {kw}...")
                    response = await client.post(self.api_url, json=payload, timeout=20.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("results", []):
                        clue = ClueItem(
                            id=str(uuid.uuid4()),
                            source="tavily",
                            title=item.get("title", "无标题"),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            publish_time=_extract_date_from_text(item.get("content", ""))
                        )
                        all_results.append(clue)
                        if on_clue:
                            try:
                                on_clue(clue)
                            except Exception:
                                pass
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    print(f"[TavilySearch] 关键词 [{kw}] 采集失败: {e}")
        
        return all_results

class GeneralSearchStrategy(BaseCollectorStrategy):
    """
    通用搜索模式：支持多引擎（Serper / Tavily / Browser）。
    """
    def __init__(self):
        self.serper_api_url = "https://google.serper.dev/search"
        self.tavily_strategy = TavilySearchStrategy()
        self._on_clue = None

    def _is_portal_like(self, title: str, url: str) -> bool:
        """Heuristic: identify portal/home/list pages to avoid deep crawling."""
        from urllib.parse import urlparse
        url_l = (url or "").lower()
        title_t = title or ""
        portal_keywords = [
            "招标网", "采购网", "公共资源交易", "政府采购", "交易中心", "平台", "网站", "中心", "门户", "首页", "频道"
        ]
        path = urlparse(url_l).path or "/"
        url_hints = ["/index", "/home", "/portal", "/channel", "/list", "/tender", "/bidding", "/zfcg"]
        if any(k in title_t for k in portal_keywords):
            return True
        if path == "/" or any(h in url_l for h in url_hints):
            return True
        return False

    def _build_query(self, constraint: BusinessConstraint) -> str:
        """根据画像构建高级搜索指令"""
        core = constraint.core_business[0] if constraint.core_business else ""
        
        # 典型的招标关键词组合
        query = f'"{core}" 招标公告 (site:*.gov.cn OR site:*.com.cn)'
        
        if constraint.geography_limits:
            loc = constraint.geography_limits[0].value
            query = f"{loc} {query}"
            
        return query

    async def _search_serper(self, client: httpx.AsyncClient, keyword: str, api_key: str) -> List[ClueItem]:
        """执行 Serper 搜索"""
        try:
            from app.core.state import state
            if state.is_paused:
                return []
        except Exception:
            pass
        print(f"[GeneralSearch-Serper] 正在搜索: {keyword}...")
        payload = {
            "q": keyword,
            "gl": "cn",
            "hl": "zh-cn",
            "autocorrect": True,
            "tbs": "qdr:m"
        }
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = await client.post(self.serper_api_url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            organic = data.get("organic", [])
            for item in organic:
                snippet = item.get("snippet", "")
                clue = ClueItem(
                    id=str(uuid.uuid4()),
                    source="serper",
                    title=item.get("title", "无标题"),
                    url=item.get("link", ""),
                    snippet=snippet,
                    publish_time=_extract_date_from_text(snippet)
                )
                results.append(clue)
                if self._on_clue:
                    try:
                        self._on_clue(clue)
                    except Exception:
                        pass
            return results
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[GeneralSearch-Serper] 失败: {e}")
            return []

    async def collect(self, constraint: BusinessConstraint, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        on_clue = kwargs.pop("on_clue", None)
        self._on_clue = on_clue
        try:
            from app.core.state import state
            if state.is_paused:
                return []
        except Exception:
            pass
        keywords = split_search_keywords(search_keywords_str)
        if not keywords:
            keywords = [self._build_query(constraint)]

        # 构造并发搜索任务列表
        search_tasks = []

        # 1. Tavily (如果配置)
        if settings.TAVILY_API_ENABLED and settings.TAVILY_API_KEY:
            search_tasks.append(self.tavily_strategy.collect(constraint, on_clue=on_clue, **kwargs))

        # 2. Serper (如果配置)
        if settings.SERPER_API_ENABLED and settings.SEARCH_API_KEY:
            async def run_serper():
                api_key = settings.SEARCH_API_KEY
                async with httpx.AsyncClient() as client:
                    group_tasks = [self._search_serper(client, kw, api_key) for kw in keywords]
                    results_groups = await asyncio.gather(*group_tasks, return_exceptions=True)
                    flat_results = []
                    for group in results_groups:
                        # 过滤掉异常对象，只处理有效结果
                        if isinstance(group, Exception):
                            print(f"[GeneralSearch-Serper] 某个关键词搜索失败: {type(group).__name__}: {str(group)}")
                            continue
                        flat_results.extend(group)
                    return flat_results
            search_tasks.append(run_serper())

        # 3. BrowserSearch (Baidu/Sogou/Bing) - 始终执行以确保搜狗覆盖
        from app.engines.collector.browser_search_strategy import BrowserSearchStrategy
        browser_strategy = BrowserSearchStrategy()
        search_tasks.append(browser_strategy.collect(constraint, on_clue=on_clue, **kwargs))

        print(f"[GeneralSearch] 启动全引擎并行采集 (Tavily={bool(settings.TAVILY_API_ENABLED and settings.TAVILY_API_KEY)} | Serper={bool(settings.SERPER_API_ENABLED and settings.SEARCH_API_KEY)} | Browser=True)")
        
        # 4. 执行并发 - 使用 return_exceptions=True 捕获异常，防止协程泄漏
        results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 5. 汇总并根据 URL 去重 - 过滤掉异常，只保留有效结果
        all_results: List[ClueItem] = []
        seen_urls = set()
        for res_group in results_list:
            # 过滤掉异常对象，只处理列表结果
            if isinstance(res_group, Exception):
                print(f"[GeneralSearch] 某个采集引擎失败: {type(res_group).__name__}: {str(res_group)}")
                continue
            if not res_group: 
                continue
            for item in res_group:
                if item.url not in seen_urls:
                    all_results.append(item)
                    seen_urls.add(item.url)

        print(f"[GeneralSearch] 并行采集结束，去重后共 {len(all_results)} 条原始线索")

        try:
            from app.core.state import state
            if state.is_paused:
                return all_results
        except Exception:
            pass

        # 6. 后处理：深度补全 (针对 Top 5)
        if all_results:
            print(f"[GeneralSearch] 启动 Playwright 融合深度扫描 (Top 5)...")
            from app.engines.collector.playwright_strategy import SiteSpecificStrategy
            playwright_scraper = SiteSpecificStrategy()
            
            # 只补全非微信链接，微信链接有专有逻辑处理
            top_urls = []
            for r in all_results:
                if "mp.weixin.qq.com" in r.url:
                    continue
                if self._is_portal_like(r.title, r.url):
                    print(f"[GeneralSearch] 跳过门户主页下钻: {r.url}")
                    continue
                top_urls.append(r.url)
                if len(top_urls) >= 5:
                    break
            if top_urls:
                deep_clues = await playwright_scraper.collect(constraint, target_urls=top_urls, on_clue=on_clue)
                url_to_deep = {c.url: c for c in deep_clues}
                for r in all_results:
                    if r.url in url_to_deep:
                        deep = url_to_deep[r.url]
                        r.full_text = deep.full_text
                        r.snippet = deep.snippet
                        if deep.publish_time:
                            r.publish_time = deep.publish_time
        
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
