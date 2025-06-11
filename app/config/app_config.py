# ========================================
# 2. app/config/app_config.py
# ========================================
"""
애플리케이션 설정 관리
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    # API 설정
    api_title: str = "hdegis-chat-backend"
    api_version: str = "1.0.0"
    api_description: str = "고압차단기 사내문서기반 QA 챗봇 백엔드 API"

    # CORS 설정
    allowed_origins: List[str] = [
        "http://localhost:5173",  # Vue.js dev server
        "http://localhost:3000",  # 추가 프론트엔드 포트
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # 요청 제한 설정
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: int = 300  # 5분

    # 로깅 설정
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # API 문서 설정
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

@lru_cache()
def get_app_config() -> AppConfig:
    """
    앱 설정 싱글톤 반환
    
    Returns:
        AppConfig: 애플리케이션 설정 인스턴스
    """
    config = AppConfig()
    
    return config

def get_cors_config(config: AppConfig) -> dict:
    """
    CORS 설정 딕셔너리 반환
    
    Args:
        config: 앱 설정
        
    Returns:
        dict: CORS 미들웨어 설정
    """
    return {
        "allow_origins": config.allowed_origins,
    }