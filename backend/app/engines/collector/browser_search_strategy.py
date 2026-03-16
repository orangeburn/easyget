import asyncio
import uuid
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.base import BaseCollectorStrategy

class BrowserSearchStrategy(BaseCollectorStrategy):
    """
    浏览器搜素策略：利用 Playwright 模拟用户在搜索引擎（如百度）的行为进行抓取。
    作为 API 缺失时的免费回退方案。
    """
    
    async def _search_baidu(self, context, keyword: str) -> List[ClueItem]:
        """由于网页结构易变，此处需增加健壮性"""
        page = await context.new_page()
        await stealth_async(page)
        
        results = []
        try:
            print(f"[BrowserSearch] 正在通过浏览器搜索: {keyword}")
            # 访问百度并搜索
            # rsv_spt=1 用于区分搜索，cl=3 用于网页搜索
            # 添加 gpc=stf 时间过滤参数，限定过去 30 天，解决数据陈旧痛点
            import time
            now_ts = int(time.time())
            past_ts = now_ts - 30 * 24 * 3600
            url = f"https://www.baidu.com/s?wd={keyword}&gpc=stf={past_ts},{now_ts}|stftype=2"
            print(f"[BrowserSearch] 访问 URL (带时间过滤): {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # 截图调试（可选，但在开发阶段由于看不到界面很有用）
            # await page.screenshot(path=f"/tmp/search_{keyword}.png")
            
            # 等待搜索结果加载
            print(f"[BrowserSearch] 等待结果容器加载...")
            try:
                await page.wait_for_selector("#content_left", timeout=15000)
            except Exception as e:
                print(f"[BrowserSearch] 未能加载内容容器 #content_left: {e}")
                # 尝试备用选择器或直接获取 body
                
            # 解析搜索条目 (百度典型的结果容器类名也可能是 t)
            items = await page.locator(".result.c-container").all()
            print(f"[BrowserSearch] 找到匹配容器数量: {len(items)}")
            
            if len(items) == 0:
                # 尝试更宽泛的选择器
                items = await page.locator("div.result").all()
                print(f"[BrowserSearch] 尝试备用选择器后找到数量: {len(items)}")
            
            for item in items[:8]: # 每次搜索取前 8 条
                try:
                    title_el = item.locator("h3 a")
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute("href")
                    
                    # 摘要信息通常在 content_left 或特定 div 中
                    abstract_el = item.locator(".c-abstract")
                    if await abstract_el.count() == 0:
                        # 百度新版结构有些是用 content-right_xxxx
                        abstract_el = item.locator(".content-right_8Zs9f") # 存根类名
                    
                    snippet = ""
                    if await abstract_el.count() > 0:
                        snippet = await abstract_el.inner_text()
                    
                    if title and href:
                        results.append(ClueItem(
                            id=str(uuid.uuid4()),
                            source="browser_search",
                            title=title.strip(),
                            url=href, # 注意：百度链接通常是加密跳转链接
                            snippet=snippet.strip() if snippet else "点击进入网页查看详情",
                            publish_time=datetime.now()
                        ))
                except Exception as e:
                    continue
                    
            print(f"[BrowserSearch] 关键词 [{keyword}] 采集完成，命中: {len(results)}")
        except Exception as e:
            print(f"[BrowserSearch] 关键词 [{keyword}] 搜索失败: {e}")
        finally:
            await page.close()
            
        return results

    async def collect(self, constraint: BusinessConstraint, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        if not search_keywords_str:
            return []
            
        import re
        keywords = [k.strip() for k in re.split(r'[,，、\s]+', search_keywords_str) if k.strip()]
        
        all_results = []
        async with async_playwright() as p:
            # 百度对无头浏览器检测较严，需要配置 stealth 并模拟真实指纹
            browser = await p.chromium.launch(
                headless=True, 
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            
            # 由于百度对并发敏感，我们稍微控制一下并发度，或者顺序执行核心词
            # 为演示性能，这里依然采用并发，但在生产环境中建议加 delay
            tasks = [self._search_baidu(context, kw) for kw in keywords]
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
