import asyncio
import urllib.parse
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.base import BaseCollectorStrategy
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import uuid
from datetime import datetime

class WechatStrategy(BaseCollectorStrategy):
    """
    微信公众号模式：针对微信生态进行专项攻坚。
    利用搜狗微信搜索作为入口，结合 Playwright 获取动态生成的真实链接或内容。
    """
    async def collect(self, constraint: BusinessConstraint, account_names: List[str] = None, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        
        # 汇总采集任务目标：具体公众号 或 行业关键词
        targets = []
        if account_names:
            targets.extend([{"type": "account", "val": a} for a in account_names])
        
        # 如果没有具体公众号，或者为了扩大覆盖面，也搜索关键词
        if search_keywords_str:
            import re
            kws = [k.strip() for k in re.split(r'[,，、\s]+', search_keywords_str) if k.strip()]
            # 限制关键词数量以免触发验证码
            targets.extend([{"type": "keyword", "val": k} for k in kws[:3]])

        if not targets:
            return []
            
        results = []
        
        async with async_playwright() as p:
            # 同样保持隐身，因为搜狗搜索的反爬非常严格
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            
            for target in targets:
                try:
                    page = await context.new_page()
                    await stealth_async(page)
                    
                    # 构造搜狗微信搜索 URL
                    # type=2 代表搜索“文章”，type=1 代表搜索“公众号”
                    query_val = target["val"]
                    if target["type"] == "account":
                        encoded_query = urllib.parse.quote(f"{query_val} 招标")
                    else:
                        encoded_query = urllib.parse.quote(f"{query_val} 招标项目")
                        
                    url = f"https://weixin.sogou.com/weixin?type=2&query={encoded_query}"
                    
                    print(f"[Wechat] 正在搜索微信资讯: {query_val} (模式: {target['type']})", flush=True)
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    
                    # TODO: 此处应拦截包含的反爬验证码逻辑
                    articles = await page.locator("ul.news-list > li").all()
                    
                    # 示范取出前两篇
                    for article in articles[:2]:
                        title_el = article.locator("h3 a")
                        title = await title_el.inner_text()
                        
                        # 创建新页面以访问真实链接，避免搜狗反爬限制
                        article_page = await context.new_page()
                        await stealth_async(article_page)
                        
                        # 搜狗微信的链接通常是跳转页，需要点击或访问
                        jump_url = await title_el.get_attribute("href")
                        if jump_url.startswith("/"):
                            jump_url = "https://weixin.sogou.com" + jump_url
                        
                        try:
                            print(f"[Wechat] 正在跳转至真实内容: {title}")
                            await article_page.goto(jump_url, timeout=30000, wait_until="domcontentloaded")
                            await asyncio.sleep(2)
                            
                            # 提取微信公众号正文
                            content_el = article_page.locator("#js_content")
                            full_text = ""
                            if await content_el.count() > 0:
                                full_text = await content_el.inner_text()
                            
                            snippet = full_text[:200].replace('\n', ' ') if full_text else "预览内容不可用"
                            
                            results.append(ClueItem(
                                id=str(uuid.uuid4()), # 生产环境建议用 URL hash
                                source="wechat",
                                title=title,
                                url=article_page.url,
                                snippet=snippet,
                                full_text=full_text,
                                publish_time=datetime.now()
                            ))
                        except Exception as e:
                            print(f"[Wechat] 提取正文失败: {e}")
                        finally:
                            await article_page.close()
                    
                except Exception as e:
                    print(f"[Wechat] 抓取微信内容失败: {str(e)}")
                finally:
                    if not page.is_closed():
                        await page.close()
                        
            await context.close()
            await browser.close()
            
        return results
