import os
from dotenv import load_dotenv

load_dotenv()

class ProxyManager:
    """
    代理轮换与环境指纹管理。
    配合已在爬虫中注入的 `playwright-stealth`，此模块用于获取代理池配置。
    """
    def __init__(self):
        # 例如格式为 http://user:pass@127.0.0.1:8080
        self.proxy_url = os.getenv("WEB_PROXY_URL")
        self.enabled = bool(self.proxy_url)

    def get_playwright_proxy_config(self) -> dict:
        """为 playwright 生成代理配置参数"""
        if not self.enabled:
            return None
            
        return {
            "server": self.proxy_url
        }
