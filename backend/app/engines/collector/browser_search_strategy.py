import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import List
import re
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.base import BaseCollectorStrategy

class BrowserSearchStrategy(BaseCollectorStrategy):
    """
    浏览器搜素策略：利用 Playwright 模拟用户在搜索引擎的行为进行抓取。
    支持多引擎并发采集：百度、Bing、搜狗。
    """

    def _extract_date_from_snippet(self, text: str):
        """从搜索摘要或特定元素中提取日期"""
        if not text:
            return None

        # 1. 处理相对时间 (例如: 1天前, 3小时前)
        if "天前" in text:
            match = re.search(r'(\d+)天前', text)
            if match:
                days = int(match.group(1))
                        return datetime.now() - timedelta(days=days)
        
        if "小时前" in text:
            match = re.search(r'(\d+)小时前', text)
            if match:
                hours = int(match.group(1))
                        return datetime.now() - timedelta(hours=hours)

        # 2. 处理绝对时间格式 (2024-03-10, 2024年3月10日)
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
    
    async def _search_baidu(self, context, keyword: str) -> List[ClueItem]:
        page = await context.new_page()
        await stealth_async(page)
        results = []
        try:
            print(f"[BrowserSearch] 正在通过百度搜索: {keyword}")
            now_ts = int(time.time())
            past_ts = now_ts - 30 * 24 * 3600
            # gpc=stf 时间过滤，限定过去 30 天
            url = f"https://www.baidu.com/s?wd={keyword}&gpc=stf={past_ts},{now_ts}|stftype=2"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector("#content_left", timeout=15000)
            except:
                pass
                
            items = await page.locator(".result.c-container").all()
            if len(items) == 0:
                items = await page.locator("div.result").all()
            
            for item in items[:8]:
                try:
                    title_el = item.locator("h3 a")
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute("href")
                    if href and href.startswith("/"):
                        href = "https://www.baidu.com" + href
                    
                    abstract_el = item.locator(".c-abstract")
                    if await abstract_el.count() == 0:
                        abstract_el = item.locator(".content-right_8Zs9f")
                    
                    snippet = ""
                    if await abstract_el.count() > 0:
                        snippet = await abstract_el.inner_text()
                    
                    if title and href:
                        if "doc360.baidu.com" in href:
                            continue
                        # 尝试从摘要或时间标签提取日期
                        # 百度结果中常有 .c-showurl 包含日期，或摘要开头有日期
                        date_str = ""
                        # 尝试寻找百度特有的日期标记
                        time_el = item.locator(".c-abstract .newTimeFactor_humanize, .c-abstract .c-showurl")
                        if await time_el.count() > 0:
                            date_str = await time_el.first.inner_text()
                        
                        pub_time = self._extract_date_from_snippet(date_str or snippet)

                        clue = ClueItem(
                            id=str(uuid.uuid4()),
                            source="baidu",
                            title=title.strip(),
                            url=href,
                            snippet=snippet.strip() if snippet else "点击进入网页查看详情",
                            publish_time=pub_time
                        )
                        results.append(clue)
                        if self._on_clue:
                            try:
                                self._on_clue(clue)
                            except Exception:
                                pass
                except:
                    continue
            print(f"[BrowserSearch] 百度完成: {keyword} | 命中: {len(results)}")
        except Exception as e:
            print(f"[BrowserSearch] 百度搜索失败: {e}")
        finally:
            await page.close()
        return results

    async def _search_bing(self, context, keyword: str) -> List[ClueItem]:
        page = await context.new_page()
        await stealth_async(page)
        results = []
        try:
            print(f"[BrowserSearch] 正在通过 Bing 搜索: {keyword}")
            url = f"https://cn.bing.com/search?q={keyword}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector("#b_results", timeout=15000)
            except:
                pass
            
            items = await page.locator("li.b_algo").all()
            for item in items[:8]:
                try:
                    title_el = item.locator("h2 a")
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute("href")
                    if href and href.startswith("/"):
                        href = "https://cn.bing.com" + href
                    snippet_el = item.locator(".b_caption p")
                    snippet = await snippet_el.inner_text() if await snippet_el.count() > 0 else ""
                    
                    if title and href:
                        if "doc360.baidu.com" in href:
                            continue
                        # 从摘要提取日期
                        pub_time = self._extract_date_from_snippet(snippet)

                        clue = ClueItem(
                            id=str(uuid.uuid4()),
                            source="bing",
                            title=title.strip(),
                            url=href,
                            snippet=snippet.strip() if snippet else "点击进入网页查看详情",
                            publish_time=pub_time
                        )
                        results.append(clue)
                        if self._on_clue:
                            try:
                                self._on_clue(clue)
                            except Exception:
                                pass
                except: continue
            print(f"[BrowserSearch] Bing 完成: {keyword} | 命中: {len(results)}")
        except Exception as e:
            print(f"[BrowserSearch] Bing 搜索失败: {e}")
        finally:
            await page.close()
        return results

    async def _search_sogou(self, context, keyword: str) -> List[ClueItem]:
        page = await context.new_page()
        await stealth_async(page)
        results = []
        try:
            print(f"[BrowserSearch] 正在通过搜狗搜索: {keyword}")
            url = f"https://www.sogou.com/web?query={keyword}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(".results", timeout=15000)
            except:
                pass
            
            items = await page.locator(".vrwrap").all()
            if not items:
                items = await page.locator(".rb").all()
                
            for item in items[:8]:
                try:
                    title_el = item.locator("h3 a")
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute("href")
                    if href and href.startswith("/"):
                        href = "https://www.sogou.com" + href
                    
                    snippet_el = item.locator(".res-desc")
                    if await snippet_el.count() == 0:
                        snippet_el = item.locator(".ft")
                    
                    snippet = await snippet_el.inner_text() if await snippet_el.count() > 0 else "查看正文详情"
                    
                    if title and href:
                        if "doc360.baidu.com" in href:
                            continue
                        # 提取日期
                        pub_time = self._extract_date_from_snippet(snippet)

                        clue = ClueItem(
                            id=str(uuid.uuid4()),
                            source="sogou",
                            title=title.strip(),
                            url=href,
                            snippet=snippet.strip(),
                            publish_time=pub_time
                        )
                        results.append(clue)
                        if self._on_clue:
                            try:
                                self._on_clue(clue)
                            except Exception:
                                pass
                except: continue
            print(f"[BrowserSearch] 搜狗完成: {keyword} | 命中: {len(results)}")
        except Exception as e:
            print(f"[BrowserSearch] 搜狗搜索失败: {e}")
        finally:
            await page.close()
        return results

    async def collect(self, constraint: BusinessConstraint, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        self._on_clue = kwargs.get("on_clue")
        if not search_keywords_str:
            return []
            
        import re
        keywords = [k.strip() for k in re.split(r'[,，、\s]+', search_keywords_str) if k.strip()]
        
        all_results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            
            import random
            for kw in keywords:
                # 随机抖动：避免高频采集触发封禁
                await asyncio.sleep(random.uniform(2.0, 5.0))
                
                # 并发执行三引擎
                tasks = [
                    self._search_baidu(context, kw),
                    self._search_bing(context, kw),
                    self._search_sogou(context, kw)
                ]
                results_groups = await asyncio.gather(*tasks)
                
                seen_urls = set()
                for group in results_groups:
                    for item in group:
                        if item.url not in seen_urls:
                            all_results.append(item)
                            seen_urls.add(item.url)
            
            await context.close()
            await browser.close()
            
        return all_results
