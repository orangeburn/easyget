from datetime import datetime
from app.core.paths import get_log_path

LOG_FILE = "backend_debug.log"

def debug_log(msg: str):
    """同时打印到控制台和文件以进行强制诊断"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg, flush=True)
    try:
        log_path = get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except:
        pass
