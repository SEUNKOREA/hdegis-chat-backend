# ========================================
# 1. app/main.py (새로 생성)
# ========================================
"""
FastAPI 애플리케이션 메인 파일
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import chat
from app.config.app_config import get_app_config, get_cors_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 설정 로드
config = get_app_config()

# FastAPI 앱 생성
app = FastAPI(
    title=config.api_title,
    version=config.api_version,
    description=config.api_description,
    docs_url=config.docs_url,
    redoc_url=config.redoc_url,
    openapi_url=config.openapi_url
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    **get_cors_config(config)
)

# 라우터 등록
app.include_router(chat.router)

# 글로벌 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return {"error": "Internal server error"}

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "hdegis-chat-backend API",
        "version": config.api_version,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "hdegis-chat-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5003,
        reload=True,
        log_level="info"
    )
