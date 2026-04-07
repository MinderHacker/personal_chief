import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.")
warnings.filterwarnings("ignore", category=UserWarning)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.api import chat

app = FastAPI(title="Personal Chief API",description="私厨",version="0.1.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.include_router(chat.router, tags=["Chat"])

@app.get("/", response_class=HTMLResponse)
def home():
    """返回前端页面"""
    static_path = Path(__file__).parent / "static" / "index.html"
    with open(static_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
def health():
    """健康检查接口"""
    return {"message": "服务正常运行！"}

if __name__ == "__main__":
    import uvicorn

    # 启动命令：python -m app.main
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)