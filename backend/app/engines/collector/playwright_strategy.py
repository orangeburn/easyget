import asyncio
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from app.engines.collector.base import BaseCollectorStrategy
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint


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
        list_hints = ["/list", "/channel", "/notice", "/bulletin", "/tender", "/bidding", "/info", "/zfcg", "/cggg"]
        return any(h in url_l for h in list_hints)

    def _replace_query_param(self, url: str, key: str, value: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query[key] = [value]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def _expand_paged_urls(self, base_url: str, max_pages: int) -> List[str]:
        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        if "page" not in query:
            return [base_url]

        pages = [self._replace_query_param(base_url, "page", str(i)) for i in range(1, max_pages + 1)]
        seen = set()
        out = []
        for page_url in pages:
            if page_url not in seen:
                seen.add(page_url)
                out.append(page_url)
        return out

    def _resolve_special_detail_url(self, href: str, base_url: str) -> Optional[str]:
        href = (href or "").strip()
        if not href:
            return None

        match = re.match(r"javascript:urlOpen\('([^']+)'\)", href)
        if match:
            bulletin_id = match.group(1)
            return f"https://ctbpsp.com/#/bulletinDetail?uuid={bulletin_id}&inpvalue=&dataSource=0&tenderAgency="

        if href.startswith("javascript:"):
            return None
        return urljoin(base_url, href)

    async def _extract_list_pages(self, page, base_url: str, max_pages: int) -> List[str]:
        """Discover pagination links from a list page."""
        anchors = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a'))
                .map(a => ({href: a.href || '', text: (a.innerText || '').trim()}))"""
        )
        base_host = urlparse(base_url).netloc
        candidates = self._expand_paged_urls(base_url, max_pages)
        for a in anchors:
            href = a.get("href", "")
            if not href:
                continue
            if urlparse(href).netloc and urlparse(href).netloc != base_host:
                continue
            h = href.lower()
            if any(k in h for k in ["page=", "p=", "pageno", "pagenum", "/page/", "index_", "page-"]):
                candidates.append(href)

        seen = set()
        pages = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                pages.append(c)
            if len(pages) >= max_pages:
                break
        return pages or [base_url]

    async def _extract_table_row_items(self, page, base_url: str) -> List[Dict[str, object]]:
        rows = await page.evaluate(
            """() => Array.from(document.querySelectorAll('table.table_text tr'))
                .slice(1)
                .map(tr => {
                    const cells = Array.from(tr.querySelectorAll('td'));
                    if (!cells.length) return null;
                    const anchor = cells[0]?.querySelector('a');
                    const title = anchor?.getAttribute('title')?.trim() || anchor?.innerText?.trim() || '';
                    const href = anchor?.getAttribute('href') || '';
                    const source = cells[3]?.innerText?.trim() || '';
                    const publish_time = cells[4]?.innerText?.trim() || '';
                    const region = cells[2]?.innerText?.trim() || '';
                    const industry = cells[1]?.innerText?.trim() || '';
                    const open_info = cells[5]?.innerText?.trim() || '';
                    return title || href ? {title, href, source, publish_time, region, industry, open_info} : null;
                })
                .filter(Boolean)"""
        )

        items = []
        for row in rows:
            detail_url = self._resolve_special_detail_url(row.get("href", ""), base_url)
            if not detail_url:
                continue
            items.append(
                {
                    "title": row.get("title", "").strip(),
                    "url": detail_url,
                    "publish_time_text": row.get("publish_time", "").strip(),
                    "snippet": " | ".join(
                        part for part in [
                            row.get("industry", "").strip(),
                            row.get("region", "").strip(),
                            row.get("source", "").strip(),
                            row.get("open_info", "").strip(),
                        ] if part
                    ),
                    "source_channel": row.get("source", "").strip(),
                }
            )
        return items

    async def _extract_detail_links(self, page, base_url: str) -> List[Dict[str, object]]:
        table_items = await self._extract_table_row_items(page, base_url)
        if table_items:
            return table_items

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
            if not href or len(text) < 4:
                continue
            abs_url = self._resolve_special_detail_url(href, base_url)
            if not abs_url:
                continue
            host = urlparse(abs_url).netloc
            if host and host != base_host and "ctbpsp.com" not in host:
                continue

            contains_kw = any(k in text for k in keywords)
            is_long_text = len(text) >= 12
            if contains_kw or is_long_text:
                detail_links.append(
                    {
                        "title": text,
                        "url": abs_url,
                        "publish_time_text": "",
                        "snippet": "",
                        "source_channel": "",
                    }
                )

        seen = set()
        out = []
        for item in detail_links:
            key = (item["url"], item["title"])
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    async def _extract_publish_time(self, page):
        """从页面提取发布日期"""
        meta_selectors = [
            "meta[property='article:published_time']",
            "meta[name='pubdate']",
            "meta[name='publishdate']",
            "meta[name='release-date']",
            "meta[name='publication-date']",
            "meta[itemprop='datePublished']",
            "meta[name='Keywords']",
        ]

        for selector in meta_selectors:
            try:
                content = await page.get_attribute(selector, "content")
                if content:
                    date_match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", content)
                    if date_match:
                        return datetime.strptime(date_match.group(1), "%Y-%m-%d")
            except Exception:
                continue

        try:
            body_text = await page.evaluate("() => document.body.innerText.substring(0, 1000)")
            patterns = [
                r"(\d{4}-\d{1,2}-\d{1,2})",
                r"(\d{4}/\d{1,2}/\d{1,2})",
                r"(\d{4}年\d{1,2}月\d{1,2}日)",
            ]
            for pattern in patterns:
                match = re.search(pattern, body_text)
                if match:
                    date_str = match.group(1)
                    date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        continue
        except Exception:
            pass

        return None

    def _parse_text_date(self, value: str) -> Optional[datetime]:
        value = (value or "").strip()
        if not value:
            return None
        match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", value)
        if not match:
            return None
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    async def _discover_list_context_urls(self, page, base_url: str) -> List[str]:
        urls = [base_url]
        base_host = urlparse(base_url).netloc
        for frame in page.frames:
            frame_url = frame.url
            if not frame_url or frame_url == base_url:
                continue
            if urlparse(frame_url).netloc != base_host:
                continue
            if self._is_list_like_url(frame_url):
                urls.append(frame_url)

        seen = set()
        out = []
        for item in urls:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    async def _build_list_row_clue(self, item: Dict[str, object]) -> ClueItem:
        return ClueItem(
            id=str(uuid.uuid4()),
            source="定向站点",
            title=str(item.get("title") or item.get("url") or ""),
            url=str(item.get("url") or ""),
            snippet=str(item.get("snippet") or "无正文"),
            full_text=None,
            publish_time=self._parse_text_date(str(item.get("publish_time_text") or "")),
        )

    async def _fetch_detail_clue(self, context, item: Dict[str, object]) -> Optional[ClueItem]:
        detail_url = str(item.get("url") or "")
        if not detail_url:
            return None

        if "ctbpsp.com/#/bulletinDetail" in detail_url:
            return await self._build_list_row_clue(item)

        dpage = await context.new_page()
        await stealth_async(dpage)
        try:
            await dpage.goto(detail_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(0.8)
            title = await dpage.title()
            if "vaptcha" in title.lower():
                return await self._build_list_row_clue(item)

            full_text = await dpage.evaluate("() => document.body.innerText")
            if "请绘制图中曲线完成人机验证" in full_text:
                return await self._build_list_row_clue(item)

            snippet = full_text[:300].replace("\n", " ") if full_text else (str(item.get("snippet") or "") or "无正文")
            pub_time = await self._extract_publish_time(dpage) or self._parse_text_date(str(item.get("publish_time_text") or ""))
            return ClueItem(
                id=str(uuid.uuid4()),
                source="定向站点",
                title=title if title else str(item.get("title") or detail_url),
                url=detail_url,
                snippet=snippet,
                full_text=full_text,
                publish_time=pub_time,
            )
        finally:
            if not dpage.is_closed():
                await dpage.close()

    async def collect(self, constraint: BusinessConstraint, target_urls: List[str] = None, **kwargs) -> List[ClueItem]:
        on_clue = kwargs.get("on_clue")
        urls_to_scan = set(target_urls or [])
        if constraint.custom_urls:
            urls_to_scan.update(constraint.custom_urls)

        if not urls_to_scan:
            return []

        results = []
        seen_keys = set()
        urls_list = list(urls_to_scan)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            )

            total_sites = len(urls_list)
            for idx, url in enumerate(urls_list, start=1):
                page = None
                try:
                    try:
                        from app.core.state import state
                        if state.is_paused:
                            break
                    except Exception:
                        pass

                    try:
                        from app.core.state import state
                        state.current_step = f"正在处理站点 ({idx}/{total_sites}): {url}"
                    except Exception:
                        pass

                    page = await context.new_page()
                    await stealth_async(page)
                    print(f"[SiteSpecific] 正在处理站点: {url}")
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)

                    if self._is_list_like_url(url):
                        list_context_urls = await self._discover_list_context_urls(page, url)
                        list_pages = []
                        for list_url in list_context_urls:
                            list_pages.extend(self._expand_paged_urls(list_url, max_pages=5))

                        dedup_pages = []
                        seen_pages = set()
                        for list_page_url in list_pages:
                            if list_page_url not in seen_pages:
                                seen_pages.add(list_page_url)
                                dedup_pages.append(list_page_url)

                        for lp in dedup_pages:
                            try:
                                from app.core.state import state
                                if state.is_paused:
                                    break
                            except Exception:
                                pass

                            lpage = await context.new_page()
                            await stealth_async(lpage)
                            try:
                                await lpage.goto(lp, timeout=30000, wait_until="domcontentloaded")
                                await asyncio.sleep(1)
                                detail_items = await self._extract_detail_links(lpage, lp)
                            finally:
                                if not lpage.is_closed():
                                    await lpage.close()

                            for item in detail_items:
                                try:
                                    from app.core.state import state
                                    if state.is_paused:
                                        break
                                except Exception:
                                    pass

                                try:
                                    clue = await self._fetch_detail_clue(context, item)
                                    if not clue:
                                        continue
                                    dedup_key = (clue.url, clue.title)
                                    if dedup_key in seen_keys:
                                        continue
                                    seen_keys.add(dedup_key)
                                    results.append(clue)
                                    if on_clue:
                                        try:
                                            on_clue(clue)
                                        except Exception:
                                            pass
                                except asyncio.CancelledError:
                                    raise
                                except Exception as e:
                                    print(f"[SiteSpecific] 抓取详情失败: {item.get('url')} | {str(e)}")
                    else:
                        title = await page.title()
                        full_text = await page.evaluate("() => document.body.innerText")
                        snippet = full_text[:200].replace("\n", " ") if full_text else "无正文"
                        pub_time = await self._extract_publish_time(page)

                        clue = ClueItem(
                            id=str(uuid.uuid4()),
                            source="定向站点",
                            title=title if title else url,
                            url=url,
                            snippet=snippet,
                            full_text=full_text,
                            publish_time=pub_time,
                        )
                        dedup_key = (clue.url, clue.title)
                        if dedup_key not in seen_keys:
                            seen_keys.add(dedup_key)
                            results.append(clue)
                            if on_clue:
                                try:
                                    on_clue(clue)
                                except Exception:
                                    pass
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    print(f"[SiteSpecific] 抓取 {url} 失败: {str(e)}")
                finally:
                    if page and not page.is_closed():
                        await page.close()

            await context.close()
            await browser.close()

        return results
