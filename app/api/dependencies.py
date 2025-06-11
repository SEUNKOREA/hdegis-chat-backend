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
from app.config.app_config import get_app_config, AppConfig
from app.config.pipeline_config import get_custom_pipeline_config
logger = logging.getLogger(__name__)


@lru_cache()
def get_chat_service() -> ChatService:
    """
    ChatService 싱글톤 인스턴스 반환
    
    Returns:
        ChatService 인스턴스
    """
    try:
        # 커스텀 설정
        pipeline_config = get_custom_pipeline_config()
        return ChatService(pipeline_config)

        # # 기본설정
        # return ChatService()
        
    except Exception as e:
        logger.error(f"ChatService 초기화 실패: {e}")
        raise


def get_current_app_config() -> AppConfig:
    """
    현재 설정 반환
    """
    return get_app_config()


# 의존성 주입용 함수들
ChatServiceDep = Depends(get_chat_service)
AppConfigDep = Depends(get_current_app_config)