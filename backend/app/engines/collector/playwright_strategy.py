import asyncio
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.base import BaseCollectorStrategy
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import uuid
from datetime import datetime

class SiteSpecificStrategy(BaseCollectorStrategy):
    """
    定向搜集模式：针对特定 URL 进行深度抓取
    集成 playwright-stealth 抹除浏览器特征
    """
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
