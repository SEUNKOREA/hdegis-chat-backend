# ========================================
# 5. app/api/dependencies.py (새로 생성)
# ========================================
"""
FastAPI 의존성 주입
"""

from functools import lru_cache
from fastapi import Depends
import logging

from app.services.chat_service import ChatService
from app.core.config import get_settings, Settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_chat_service() -> ChatService:
    """
    ChatService 싱글톤 인스턴스 반환
    
    Returns:
        ChatService 인스턴스
    """
    try:
        return ChatService()
    except Exception as e:
        logger.error(f"ChatService 초기화 실패: {e}")
        raise


def get_current_settings() -> Settings:
    """
    현재 설정 반환
    
    Returns:
        Settings 인스턴스
    """
    return get_settings()


# 의존성 주입용 함수들
ChatServiceDep = Depends(get_chat_service)
SettingsDep = Depends(get_current_settings)