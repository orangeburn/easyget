import asyncio
import os
import sys
from pathlib import Path

import uvicorn


BACKEND_PORT = int(os.getenv("EASYGET_BACKEND_PORT", "8000"))
CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=BACKEND_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
