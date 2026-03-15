import asyncio
from typing import List, Dict, Any
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

    async def run_all_tasks(self, constraint: BusinessConstraint, config: Dict[str, Any]) -> List[ClueItem]:
        """
        并行发起三个模式的抓取任务，收集并融合为一个 List 输出。
        :param config: 含有定向 URL 和待查公众号的配置信息
        """
        target_urls = config.get("target_urls", [])
        wechat_accounts = config.get("wechat_accounts", [])
        search_keywords = config.get("search_keywords", "")
        
        # 使用 asyncio.gather 实现多数据源并发采集
        print(f"[Dispatcher] 启动混合采集任务: 搜索词({len(search_keywords.split(',')) if search_keywords else 0}) | 监控站({len(target_urls)}) | 公众号({len(wechat_accounts)})")
        results = await asyncio.gather(
            self.general_strategy.collect(constraint, search_keywords=search_keywords),
            self.site_strategy.collect(constraint, target_urls),
            self.wechat_strategy.collect(constraint, wechat_accounts, search_keywords=search_keywords)
        )
        
        # 展平所有的 List 结果
        all_clues: List[ClueItem] = []
        for result_group in results:
            all_clues.extend(result_group)
            
        print(f"[Dispatcher] 本次调度完成，共采集到 {len(all_clues)} 条线索。")
        return all_clues
