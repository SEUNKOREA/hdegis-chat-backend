# ========================================
# 2. app/core/config.py (새로 생성)
# ========================================
"""
애플리케이션 설정 관리
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    api_title: str = "hdegis-chat-backend"
    api_version: str = "1.0.0"
    
    # CORS 설정
    allowed_origins: List[str] = [
        "http://localhost:5173",  # Vue.js dev server
        "http://localhost:3000",  # 추가 프론트엔드 포트
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # 기존 환경변수들 (secrets_config.py에서 가져옴)
    es_host: str = ""
    es_user: str = ""
    es_password: str = ""
    project_id: str = ""
    location: str = ""
    minio_host: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = True
    
    # Google Cloud 인증 파일 경로 (추가)
    google_application_credentials: Optional[str] = None
    
    # 추가 설정
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: int = 300  # 5분
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환"""
    return Settings()