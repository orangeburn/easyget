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
import random
import re

class WechatStrategy(BaseCollectorStrategy):
    """
    微信公众号模式：针对微信生态进行专项攻坚。
    利用搜狗微信搜索作为入口，结合 Playwright 获取动态生成的真实链接或内容。
    """
    async def collect(self, constraint: BusinessConstraint, account_names: List[str] = None, **kwargs) -> List[ClueItem]:
        search_keywords_str = kwargs.get("search_keywords", "")
        on_clue = kwargs.get("on_clue")
        
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
        
        def _clean_url(url: str) -> str:
            """剥离微信链接中的临时参数"""
            if "mp.weixin.qq.com" not in url:
                return url
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            # 保留核心参数
            keep_params = ["__biz", "mid", "idx", "sn", "chksm"]
            new_params = {k: params[k] for k in keep_params if k in params}
            
            # 如果是 /s/ 类型的短链接，不需要处理参数
            if "/s/" in parsed.path and not parsed.query:
                return url
                
            query_string = urllib.parse.urlencode(new_params, doseq=True)
            return urllib.parse.urlunparse(parsed._replace(query=query_string))

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
                    import random
                    await asyncio.sleep(random.uniform(1.5, 3.0))

                    # TODO: 此处应拦截包含的反爬验证码逻辑
                    articles = await page.locator("ul.news-list > li").all()
                    
                    # 取出前 5 篇
                    for article in articles[:5]:
                        title_el = article.locator("h3 a")
                        if await title_el.count() == 0:
                            continue
                        title = await title_el.inner_text()
                        
                        # 创建新页面以访问真实链接
                        article_page = await context.new_page()
                        await stealth_async(article_page)
                        
                        jump_url = await title_el.get_attribute("href")
                        if jump_url.startswith("/"):
                            jump_url = "https://weixin.sogou.com" + jump_url
                        
                        try:
                            print(f"[Wechat] 正在跳转至真实内容: {title}")
                            await article_page.goto(jump_url, timeout=30000, wait_until="domcontentloaded")
                            await asyncio.sleep(random.uniform(1.0, 2.5))
                            
                            # 提取微信公众号正文
                            content_el = article_page.locator("#js_content")
                            full_text = ""
                            if await content_el.count() > 0:
                                full_text = await content_el.inner_text()
                            snippet = full_text[:300].replace('\n', ' ') if full_text else "无正文"
                            
                            
                            # 尝试获取永久链接 (og:url 或 msg_link)
                            final_url = article_page.url
                            try:
                                meta_url = await article_page.eval_on_selector(
                                    'meta[property="og:url"]', 
                                    'el => el.getAttribute("content")'
                                )
                                if meta_url:
                                    final_url = meta_url
                            except:
                                pass
                                
                            
                            # 提取发布时间 (WeChat 文章通常在 JavaScript 变量中带有 ct)
                            pub_time = datetime.now()
                            try:
                                # 尝试从 window.ct 或其他变量中提取
                                ct = await article_page.evaluate('() => window.ct || ""')
                                if ct:
                                    pub_time = datetime.fromtimestamp(int(ct))
                                else:
                                    # 如果没有 ct，尝试寻找页面上的时间文本（通常在 publish_time 元素中）
                                    time_el = article_page.locator("#publish_time")
                                    if await time_el.count() > 0:
                                        time_text = await time_el.inner_text()
                                        # 这里可以根据需要进行日期解析，暂时保留原始逻辑或简单处理
                                        # 微信的时间显示通常比较特殊，但 ct 是最稳妥的
                                        pass
                            except:
                                pass

                            cleaned_url = _clean_url(final_url)

                            clue = ClueItem(
                                id=str(uuid.uuid4()),
                                source="wechat",
                                title=title,
                                url=cleaned_url,
                                snippet=snippet,
                                full_text=full_text,
                                publish_time=pub_time
                            )
                            results.append(clue)
                            if on_clue:
                                try:
                                    on_clue(clue)
                                except Exception:
                                    pass
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
