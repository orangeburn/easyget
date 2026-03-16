import asyncio
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.base import BaseCollectorStrategy
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import uuid
from datetime import datetime
from urllib.parse import urlparse, urljoin

class SiteSpecificStrategy(BaseCollectorStrategy):
    """
    定向搜集模式：针对特定 URL 进行深度抓取
    集成 playwright-stealth 抹除浏览器特征
    """
    def _is_list_like_url(self, url: str) -> bool:
        url_l = (url or "").lower()
        path = urlparse(url_l).path or "/"
        if path == "/":
            return True
        list_hints = ["/list", "/channel", "/notice", "/bulletin", "/tender", "/bidding", "/info", "/zfcg", "/cggg", "/cggg"]
        return any(h in url_l for h in list_hints)

    async def _extract_list_pages(self, page, base_url: str, max_pages: int) -> List[str]:
        """Discover pagination links from a list page."""
        anchors = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a'))
                .map(a => ({href: a.href || '', text: (a.innerText || '').trim()}))"""
        )
        base_host = urlparse(base_url).netloc
        candidates = []
        for a in anchors:
            href = a.get("href", "")
            if not href:
                continue
            if urlparse(href).netloc and urlparse(href).netloc != base_host:
                continue
            h = href.lower()
            if any(k in h for k in ["page=", "p=", "pageno", "pagenum", "/page/", "index_", "page-"]):
                candidates.append(href)
        # Dedup and keep a few
        seen = set()
        pages = [base_url]
        for c in candidates:
            if c not in seen and c != base_url:
                seen.add(c)
                pages.append(c)
            if len(pages) >= max_pages:
                break
        return pages

    async def _extract_detail_links(self, page, base_url: str) -> List[str]:
        anchors = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a'))
                .map(a => ({href: a.getAttribute('href') || '', text: (a.innerText || '').trim()}))"""
        )
        base_host = urlparse(base_url).netloc
        keywords = ["招标", "采购", "公告", "成交", "中标", "询价", "磋商", "意向", "项目", "结果", "答疑", "更正", "合同"]
        detail_links = []
        for a in anchors:
            href = a.get("href", "")
            text = a.get("text", "")
            if not href or href.startswith("javascript:") or len(text) < 4:
                continue
            abs_url = urljoin(base_url, href)
            host = urlparse(abs_url).netloc
            if host and host != base_host:
                continue
            
            # 放宽条件：链接文本足够长（像标题），或者命中更多业务相关的关键字
            # 不再要求链接里必须带招标字眼，因为很多平台通过 ID 路由
            blob = text
            contains_kw = any(k in blob for k in keywords)
            is_long_text = len(blob) >= 12 # 中文标题通常比较长，如果是导航或页码通常很短
            
            if contains_kw or is_long_text:
                detail_links.append(abs_url)
        # Dedup while preserving order
        seen = set()
        out = []
        for u in detail_links:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    async def collect(self, constraint: BusinessConstraint, target_urls: List[str] = None, **kwargs) -> List[ClueItem]:
        # 合并传入的 URL 和 画像中保存的自定义 URL
        urls_to_scan = set(target_urls or [])
        if constraint.custom_urls:
            urls_to_scan.update(constraint.custom_urls)
            
        if not urls_to_scan:
            return []
            
        results = []
        
        async with async_playwright() as p:
            # 启动无头浏览器
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            
            for url in urls_to_scan:
                try:
                    page = await context.new_page()
                    await stealth_async(page)

                    print(f"[SiteSpecific] 正在处理站点: {url}")
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)

                    # 如果是列表/门户页，抓取最多 5 页列表并进入详情
                    if self._is_list_like_url(url):
                        list_pages = await self._extract_list_pages(page, url, max_pages=5)
                        for lp in list_pages:
                            if lp != url:
                                await page.goto(lp, timeout=30000, wait_until="domcontentloaded")
                                await asyncio.sleep(1)
                            detail_links = await self._extract_detail_links(page, lp)
                            # 每页全抓
                            for detail_url in detail_links:
                                try:
                                    dpage = await context.new_page()
                                    await stealth_async(dpage)
                                    await dpage.goto(detail_url, timeout=30000, wait_until="domcontentloaded")
                                    await asyncio.sleep(1)
                                    title = await dpage.title()
                                    full_text = await dpage.evaluate("() => document.body.innerText")
                                    snippet = full_text[:200].replace('\n', ' ') if full_text else "无正文"
                                    results.append(ClueItem(
                                        id=str(uuid.uuid4()),
                                        source="site",
                                        title=title if title else detail_url,
                                        url=detail_url,
                                        snippet=snippet,
                                        full_text=full_text,
                                        publish_time=datetime.now()
                                    ))
                                except Exception as e:
                                    print(f"[SiteSpecific] 抓取详情失败: {detail_url} | {str(e)}")
                                finally:
                                    if not dpage.is_closed():
                                        await dpage.close()
                    else:
                        title = await page.title()
                        full_text = await page.evaluate("() => document.body.innerText")
                        snippet = full_text[:200].replace('\n', ' ') if full_text else "无正文"

                        results.append(ClueItem(
                            id=str(uuid.uuid4()),
                            source="site",
                            title=title if title else url,
                            url=url,
                            snippet=snippet,
                            full_text=full_text,
                            publish_time=datetime.now()
                        ))
                    
                except Exception as e:
                    print(f"[SiteSpecific] 抓取 {url} 失败: {str(e)}")
                finally:
                    if not page.is_closed():
                        await page.close()
                        
            await context.close()
            await browser.close()
            
        return results
