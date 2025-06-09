"""
검색 엔진 추상화 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseSearcher(ABC):
    """검색 엔진의 추상 인터페이스"""
    
    @abstractmethod
    def ping(self) -> bool:
        """
        연결 상태 확인
        
        Returns:
            bool: 연결 성공 여부
        """
        pass
    
    @abstractmethod
    def keyword_search(
        self,
        index_name: str,
        query: str,
        text_fields: List[str],
        top_k: int,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        키워드 검색
        
        Args:
            index_name: 인덱스명
            query: 검색 쿼리
            text_fields: 텍스트 검색 대상 필드들
            top_k: 반환할 결과 개수
            filters: 적용할 필터들
            
        Returns:
            List[Dict]: 검색 결과
        """
        pass
    
    @abstractmethod
    def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        vector_field: str,
        top_k: int,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        벡터 검색
        
        Args:
            index_name: 인덱스명
            query_vector: 쿼리 벡터
            vector_field: 벡터 필드명
            top_k: 반환할 결과 개수
            filters: 적용할 필터들
            
        Returns:
            List[Dict]: 검색 결과
        """
        pass
    
    @abstractmethod
    def hybrid_search(
        self,
        index_name: str,
        query: str,
        query_vector: List[float],
        text_fields: List[str],
        vector_field: str,
        top_k: int,
        vector_weight: float = 0.3,
        text_weight: float = 0.7,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (키워드 + 벡터)
        
        Args:
            index_name: 인덱스명
            query: 텍스트 쿼리
            query_vector: 쿼리 벡터
            text_fields: 텍스트 검색 대상 필드들
            vector_field: 벡터 필드명
            top_k: 반환할 결과 개수
            vector_weight: 벡터 검색 가중치
            text_weight: 텍스트 검색 가중치
            filters: 적용할 필터들
            
        Returns:
            List[Dict]: 검색 결과
        """
        pass
    
    @abstractmethod
    def expand_search_results(
        self,
        index_name: str,
        hits: List[Dict[str, Any]],
        tolerance: int
    ) -> List[Dict[str, Any]]:
        """
        검색 결과를 페이지 단위로 확장
        
        Args:
            index_name: 인덱스명
            hits: 원본 검색 결과
            tolerance: 확장할 페이지 범위
            
        Returns:
            List[Dict]: 확장된 검색 결과
        """
        pass