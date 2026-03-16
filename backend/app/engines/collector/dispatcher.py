import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.strategies import GeneralSearchStrategy
from app.engines.collector.playwright_strategy import SiteSpecificStrategy
from app.engines.collector.wechat_strategy import WechatStrategy

class CollectionDispatcher:
    """
    信息采集引擎 - 调度器
    负责驱动三模引擎（全网/定向/微信）同步或异步采集，进行资源池调度
    """
    def __init__(self):
        self.general_strategy = GeneralSearchStrategy()
        self.site_strategy = SiteSpecificStrategy()
        self.wechat_strategy = WechatStrategy()

    def _is_portal_like(self, clue: ClueItem) -> bool:
        """Heuristic: identify portal/list pages to auto-enroll as target sites."""
        url = (clue.url or "").lower()
        title = (clue.title or "")
        portal_keywords = [
            "招标网", "采购网", "公共资源交易", "政府采购", "交易中心", "平台", "网站", "中心", "门户", "首页", "频道"
        ]
        path = urlparse(url).path or "/"
        url_hints = ["/index", "/home", "/portal", "/channel", "/list", "/tender", "/bidding", "/zfcg"]
        if any(k in title for k in portal_keywords):
            return True
        if path == "/" or any(h in url for h in url_hints):
            return True
        return False

    def _extract_portal_urls(self, clues: List[ClueItem]) -> List[str]:
        urls = []
        for c in clues:
            if c.url and self._is_portal_like(c):
                urls.append(c.url)
        # Deduplicate while preserving order
        seen = set()
        out = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    async def run_all_tasks(self, constraint: BusinessConstraint, config: Dict[str, Any]) -> List[ClueItem]:
        """
        并行发起三个模式的抓取任务，收集并融合为一个 List 输出。
        :param config: 含有定向 URL 和待查公众号的配置信息
        """
        if constraint is None:
            print("[Dispatcher] 缺少企业画像（constraint=None），本次采集已跳过。")
            return []
        target_urls = config.get("target_urls", [])
        wechat_accounts = config.get("wechat_accounts", [])
        search_keywords = config.get("search_keywords", "")

        # 1) 先执行全网搜索，自动识别门户/列表站点加入定向
        print(f"[Dispatcher] 启动混合采集任务: 搜索词({len(search_keywords.split(',')) if search_keywords else 0}) | 监控站({len(target_urls)}) | 公众号({len(wechat_accounts)})")
        general_results = await self.general_strategy.collect(constraint, search_keywords=search_keywords)
        auto_portals = self._extract_portal_urls(general_results)

        # 合并用户指定与自动识别的站点
        merged_targets = list(target_urls) + auto_portals
        # 去重
        seen = set()
        merged_targets = [u for u in merged_targets if not (u in seen or seen.add(u))]

        # 2) 站点与公众号并发
        site_results, wechat_results = await asyncio.gather(
            self.site_strategy.collect(constraint, merged_targets),
            self.wechat_strategy.collect(constraint, wechat_accounts, search_keywords=search_keywords)
        )

        # 3) 汇总
        all_clues: List[ClueItem] = []
        all_clues.extend(general_results)
        all_clues.extend(site_results)
        all_clues.extend(wechat_results)

        print(f"[Dispatcher] 本次调度完成，共采集到 {len(all_clues)} 条线索。")
        return all_clues
