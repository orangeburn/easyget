from typing import Optional, Dict
from app.core.config import settings

class ProxyManager:
    """
    代理管理器存根：后续可扩展为动态代理池集成。
    目前主要从配置中读取静态代理 URL。
    """
    def __init__(self):
        self.proxy_url = settings.WEB_PROXY_URL

    def get_proxy_settings(self) -> Optional[Dict[str, str]]:
        """
        返回 playwright 或 httpx 通用的代理配置字典。
        """
        if not self.proxy_url:
            return None
        
        return {
            "server": self.proxy_url
        }

proxy_manager = ProxyManager()
