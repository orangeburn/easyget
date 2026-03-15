import os
from datetime import datetime

LOG_FILE = "backend_debug.log"

def debug_log(msg: str):
    """同时打印到控制台和文件以进行强制诊断"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg, flush=True)
    try:
        # 确保在 backend 目录下创建日志
        log_path = os.path.join(os.getcwd(), LOG_FILE)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except:
        pass
