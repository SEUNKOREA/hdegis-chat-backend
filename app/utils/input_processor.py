"""
입력 처리 유틸리티
"""

from typing import Optional
import logging
from google.cloud import translate_v2 as translate

logger = logging.getLogger(__name__)


class InputProcessor:
    """사용자 입력 처리 클래스"""
    
    def __init__(self):
        """번역 클라이언트 초기화"""
        try:
            self.translate_client = translate.Client()
            logger.info("Google 번역 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"Google 번역 클라이언트 초기화 실패: {e}")
            self.translate_client = None
    
    def detect_language(self, text: str) -> Optional[str]:
        """
        텍스트의 언어 감지
        
        Args:
            text: 언어를 감지할 텍스트
            
        Returns:
            str: 감지된 언어 코드 (예: 'ko', 'en')
        """
        if not self.translate_client:
            logger.warning("번역 클라이언트가 초기화되지 않음")
            return None
        
        try:
            result = self.translate_client.detect_language(text)
            return result['language']
        except Exception as e:
            logger.error(f"언어 감지 실패: {e}")
            return None
    
    def translate_text(
        self,
        text: str,
        target_language: str = 'en',
        source_language: Optional[str] = None
    ) -> str:
        """
        텍스트 번역
        
        Args:
            text: 번역할 텍스트
            target_language: 목표 언어 코드
            source_language: 원본 언어 코드 (None이면 자동 감지)
            
        Returns:
            str: 번역된 텍스트 (번역이 필요하지 않으면 원본 반환)
        """
        if not self.translate_client:
            logger.warning("번역 클라이언트가 없어서 원본 텍스트 반환")
            return text
        
        try:
            # 언어 감지
            if source_language is None:
                detected_lang = self.detect_language(text)
                if detected_lang == target_language:
                    return text
            elif source_language == target_language:
                return text
            
            # 번역 수행
            result = self.translate_client.translate(
                text,
                target_language=target_language,
                source_language=source_language
            )
            return result['translatedText']
            
        except Exception as e:
            logger.error(f"번역 실패: {e}")
            return text  # 실패 시 원본 반환
    
    def clean_text(self, text: str) -> str:
        """
        텍스트 정리 (공백, 특수문자 등)
        
        Args:
            text: 정리할 텍스트
            
        Returns:
            str: 정리된 텍스트
        """
        if not text:
            return ""
        
        # 기본적인 텍스트 정리
        cleaned = text.strip()
        
        # 연속된 공백을 하나로 통합
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned