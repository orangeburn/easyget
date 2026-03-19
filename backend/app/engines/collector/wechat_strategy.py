import asyncio
import re
import urllib.parse
import uuid
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from app.engines.collector.base import BaseCollectorStrategy
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.utils.keywords import split_search_keywords


class WechatStrategy(BaseCollectorStrategy):
    """
    微信公众号模式：针对微信生态进行专项攻坚。
    优先满足“指定公众号 + 关键词”的最新文章监控需求。
    """

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"[\s\W_]+", "", (value or "").lower())

    def _account_match_score(self, expected: str, actual: str) -> float:
        expected_n = self._normalize_text(expected)
        actual_n = self._normalize_text(actual)
        if not expected_n or not actual_n:
            return 0.0
        if expected_n == actual_n:
            return 1.0
        if expected_n in actual_n or actual_n in expected_n:
            return 0.9
        return SequenceMatcher(None, expected_n, actual_n).ratio()

    def _is_matching_account(self, expected: str, actual: str) -> bool:
        # 微信文章页里的公众号名可能保留历史名称，不能只按当前名称做精确匹配。
        return self._account_match_score(expected, actual) >= 0.72

    def _keyword_hit(self, title: str, summary: str, full_text: str, keywords: List[str]) -> bool:
        if not keywords:
            return True
        blob = " ".join(filter(None, [title, summary, full_text]))
        blob_n = self._normalize_text(blob)
        return any(self._normalize_text(k) in blob_n for k in keywords if self._normalize_text(k))

    def _clean_url(self, url: str) -> str:
        """剥离微信链接中的临时参数，但保留可访问的核心链接。"""
        if "mp.weixin.qq.com" not in url:
            return url
        parsed = urllib.parse.urlparse(url)
        if "/s/" in parsed.path and not parsed.query:
            return url

        params = urllib.parse.parse_qs(parsed.query)
        keep_params = ["__biz", "mid", "idx", "sn", "chksm"]
        new_params = {k: params[k] for k in keep_params if k in params}
        if not new_params:
            return url

        query_string = urllib.parse.urlencode(new_params, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=query_string))

    def _build_targets(self, account_names: List[str], search_keywords_str: str) -> List[Dict[str, object]]:
        account_names = [a.strip() for a in (account_names or []) if a and a.strip()]
        keywords = [k.strip() for k in split_search_keywords(search_keywords_str) if k.strip()][:3]

        targets: List[Dict[str, object]] = []
        if account_names:
            for account in account_names:
                targets.append(
                    {
                        "type": "account",
                        "query": account,
                        "account": account,
                        "keywords": keywords,
                        "source_label": "定向公号",
                        "max_pages": 3,
                    }
                )
                if keywords:
                    for keyword in keywords:
                        targets.append(
                            {
                                "type": "account_keyword",
                                "query": f"{account} {keyword}",
                                "account": account,
                                "keywords": [keyword],
                                "source_label": "定向公号",
                                "max_pages": 2,
                            }
                        )
            return targets

        for keyword in keywords:
            targets.append(
                {
                    "type": "keyword",
                    "query": keyword,
                    "account": None,
                    "keywords": [keyword],
                    "source_label": "wechat",
                    "max_pages": 2,
                }
            )
        return targets

    async def _extract_card_source(self, article) -> str:
        selectors = [
            ".s-p .all-time-y2",
            ".account",
            ".wx-name",
        ]
        for selector in selectors:
            try:
                locator = article.locator(selector)
                if await locator.count() > 0:
                    text = (await locator.first.inner_text()).strip()
                    if text:
                        return text
            except Exception:
                continue
        return ""

    async def _extract_card_publish_time(self, article) -> Optional[datetime]:
        try:
            time_text = (await article.locator(".s-p .s2").first.inner_text()).strip()
        except Exception:
            return None

        if not time_text:
            return None
        if "天前" in time_text:
            match = re.search(r"(\d+)天前", time_text)
            if match:
                return datetime.now() - timedelta(days=int(match.group(1)))
        if "小时前" in time_text:
            match = re.search(r"(\d+)小时前", time_text)
            if match:
                return datetime.now() - timedelta(hours=int(match.group(1)))

        date_match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", time_text)
        if date_match:
            try:
                return datetime.strptime(date_match.group(1), "%Y-%m-%d")
            except ValueError:
                return None
        return None

    async def _extract_page_account_name(self, article_page) -> str:
        selectors = ["#js_name", "#profileBt #js_name"]
        for selector in selectors:
            try:
                locator = article_page.locator(selector)
                if await locator.count() > 0:
                    text = (await locator.first.inner_text()).strip()
                    if text:
                        return text
            except Exception:
                continue
        return ""

    async def _extract_page_publish_time(self, article_page) -> Optional[datetime]:
        try:
            locator = article_page.locator("#publish_time")
            if await locator.count() > 0:
                time_text = (await locator.first.inner_text()).strip()
                match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", time_text)
                if match:
                    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except Exception:
            pass
        return None

    async def _extract_article(self, article, context, target: Dict[str, object]) -> Optional[ClueItem]:
        title_el = article.locator("h3 a")
        if await title_el.count() == 0:
            return None

        title = (await title_el.inner_text()).strip()
        summary = ""
        try:
            summary = (await article.locator("p.txt-info").first.inner_text()).strip()
        except Exception:
            summary = ""

        account_source = await self._extract_card_source(article)
        expected_account = target.get("account")
        keywords = target.get("keywords") or []

        jump_url = await title_el.get_attribute("href")
        if not jump_url:
            return None
        if jump_url.startswith("/"):
            jump_url = "https://weixin.sogou.com" + jump_url

        article_page = await context.new_page()
        await stealth_async(article_page)
        try:
            print(f"[Wechat] 正在跳转至真实内容: {title}")
            await article_page.goto(jump_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(1.2)

            content_el = article_page.locator("#js_content")
            full_text = ""
            if await content_el.count() > 0:
                full_text = await content_el.inner_text()

            page_account_name = await self._extract_page_account_name(article_page)
            if expected_account:
                matched_account = page_account_name or account_source
                if not self._is_matching_account(str(expected_account), matched_account):
                    return None

            if not self._keyword_hit(title, summary, full_text, keywords):
                return None

            snippet = full_text[:300].replace("\n", " ") if full_text else (summary or "无正文")

            final_url = article_page.url
            try:
                meta_url = await article_page.eval_on_selector(
                    'meta[property="og:url"]',
                    "el => el.getAttribute('content')",
                )
                if meta_url:
                    final_url = meta_url
            except Exception:
                pass

            pub_time = (
                await self._extract_page_publish_time(article_page)
                or await self._extract_card_publish_time(article)
                or datetime.now()
            )
            try:
                ct = await article_page.evaluate("() => window.ct || ''")
                if ct:
                    pub_time = datetime.fromtimestamp(int(ct))
            except Exception:
                pass

            return ClueItem(
                id=str(uuid.uuid4()),
                source=str(target.get("source_label") or "wechat"),
                title=title,
                url=self._clean_url(final_url),
                snippet=snippet,
                full_text=full_text,
                publish_time=pub_time,
            )
        finally:
            await article_page.close()

    async def collect(self, constraint: BusinessConstraint, account_names: List[str] = None, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        on_clue = kwargs.get("on_clue")

        targets = self._build_targets(account_names, search_keywords_str)
        if not targets:
            return []

        results: List[ClueItem] = []
        seen_keys = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            )

            for target in targets:
                page = None
                try:
                    try:
                        from app.core.state import state

                        if state.is_paused:
                            break
                    except Exception:
                        pass

                    page = await context.new_page()
                    await stealth_async(page)

                    query = str(target["query"])
                    max_pages = int(target.get("max_pages") or 1)
                    for page_no in range(1, max_pages + 1):
                        page_url = (
                            f"https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(query)}"
                            f"&page={page_no}&ie=utf8"
                        )
                        print(
                            f"[Wechat] 正在搜索微信资讯: {query} (模式: {target['type']}, 页码: {page_no})",
                            flush=True,
                        )
                        await page.goto(page_url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(1.8)

                        articles = await page.locator("ul.news-list > li").all()
                        if not articles:
                            break

                        for article in articles[:10]:
                            try:
                                from app.core.state import state

                                if state.is_paused:
                                    break
                            except Exception:
                                pass

                            try:
                                clue = await self._extract_article(article, context, target)
                                if clue is None:
                                    continue

                                dedup_key = (
                                    self._normalize_text(clue.url or ""),
                                    self._normalize_text(clue.title or ""),
                                )
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
                                print(f"[Wechat] 提取正文失败: {e}")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    print(f"[Wechat] 抓取微信内容失败: {str(e)}")
                finally:
                    if page and not page.is_closed():
                        await page.close()

            await context.close()
            await browser.close()

        results.sort(key=lambda item: item.publish_time or datetime.min, reverse=True)
        return results
