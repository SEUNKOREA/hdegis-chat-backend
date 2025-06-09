"""
임베딩 모델 추상화 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseEmbedder(ABC):
    """임베딩 모델의 추상 인터페이스"""
    
    @abstractmethod
    def embed_text(
        self,
        text: str,
        task: str = "RETRIEVAL_DOCUMENT",
        dimensionality: Optional[int] = None
    ) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
            task: 임베딩 태스크 (RETRIEVAL_DOCUMENT 등)
            dimensionality: 출력 차원 수 (None이면 기본값 사용)
            
        Returns:
            List[float]: 임베딩 벡터
        """
        pass
    
    @abstractmethod
    def embed_batch(
        self,
        texts: List[str],
        task: str = "RETRIEVAL_DOCUMENT",
        dimensionality: Optional[int] = None
    ) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩
        
        Args:
            texts: 임베딩할 텍스트 목록
            task: 임베딩 태스크
            dimensionality: 출력 차원 수
            
        Returns:
            List[List[float]]: 임베딩 벡터 목록
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """모델명 반환"""
        pass
    
    @property
    @abstractmethod
    def need_translation(self) -> bool:
        """번역이 필요한지 여부 반환"""
        pass
    
    @property
    @abstractmethod
    def default_dimensionality(self) -> int:
        """기본 차원 수 반환"""
        pass