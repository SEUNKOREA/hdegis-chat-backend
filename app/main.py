# ========================================
# 1. app/main.py (새로 생성)
# ========================================
"""
FastAPI 애플리케이션 메인 파일
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from dotenv import load_dotenv
load_dotenv()
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
cors_config = get_cors_config(config)

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
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"],
)

# 라우터 등록
app.include_router(chat.router)

# OPTIONS 요청 처리를 위한 미들웨어 (필요시)
@app.middleware("http")
async def cors_handler(request, call_next):
    response = await call_next(request)
    
    # 추가 헤더 설정 (스트리밍용)
    response.headers["Access-Control-Allow-Origin"] = "*"  # 또는 특정 도메인
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

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
        port=5002,
        reload=True,
        log_level="info"
    )
