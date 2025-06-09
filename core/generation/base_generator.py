"""
텍스트 생성 모델 추상화 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from google.genai import types


class BaseGenerator(ABC):
    """텍스트 생성 모델의 추상 인터페이스"""
    
    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        텍스트 생성
        
        Args:
            prompt: 입력 프롬프트
            model: 사용할 모델명 (None이면 기본 모델 사용)
            generation_config: 생성 설정
            
        Returns:
            str: 생성된 텍스트
        """
        pass
    
    @abstractmethod
    def generate_multimodal(
        self,
        parts: List[types.Part],
        model: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        멀티모달 생성 (텍스트 + 이미지)
        
        Args:
            parts: 입력 파트들 (텍스트, 이미지 등)
            model: 사용할 모델명
            generation_config: 생성 설정
            
        Returns:
            str: 생성된 텍스트
        """
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """기본 모델명 반환"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """지원하는 모델 목록 반환"""
        pass