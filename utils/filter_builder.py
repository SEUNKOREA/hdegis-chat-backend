"""
검색 필터 구성 유틸리티
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FilterBuilder:
    """검색 필터 구성 클래스"""
    
    @staticmethod
    def create_folder_filters(user_filter: str, field_name: str = "gcs_path") -> List[Dict[str, Any]]:
        """
        사용자 필터 문자열에서 폴더 기반 필터 생성
        
        Args:
            user_filter: 사용자 입력 필터 ("폴더A/서브폴더1 & 폴더B/서브폴더2" 형태)
            field_name: 필터를 적용할 필드명
            
        Returns:
            List[Dict]: Elasticsearch match_phrase 필터 목록
        """
        if not user_filter or not user_filter.strip():
            return []
        
        try:
            # '&' 기준으로 분리
            filter_parts = user_filter.strip().split('&')
            
            # 각 부분을 정리하고 마지막 경로 추출
            filters = []
            for part in filter_parts:
                cleaned_part = part.strip()
                if cleaned_part:
                    # '/' 기준으로 분리하여 마지막 값 추출
                    last_folder = cleaned_part.split('/')[-1].strip()
                    if last_folder:
                        filters.append({
                            'match_phrase': {field_name: last_folder}
                        })
            
            logger.debug(f"생성된 필터: {filters}")
            return filters
            
        except Exception as e:
            logger.error(f"필터 생성 실패: {e}")
            return []
    
    @staticmethod
    def create_term_filters(values: List[str], field_name: str) -> List[Dict[str, Any]]:
        """
        특정 값들에 대한 term 필터 생성
        
        Args:
            values: 필터링할 값들
            field_name: 필터를 적용할 필드명
            
        Returns:
            List[Dict]: Elasticsearch term 필터 목록
        """
        if not values:
            return []
        
        return [
            {'term': {field_name: value}}
            for value in values if value and value.strip()
        ]
    
    @staticmethod
    def create_range_filter(
        field_name: str,
        min_value: Any = None,
        max_value: Any = None,
        include_min: bool = True,
        include_max: bool = True
    ) -> Dict[str, Any]:
        """
        범위 필터 생성
        
        Args:
            field_name: 필터를 적용할 필드명
            min_value: 최소값
            max_value: 최대값
            include_min: 최소값 포함 여부
            include_max: 최대값 포함 여부
            
        Returns:
            Dict: Elasticsearch range 필터
        """
        range_clause = {}
        
        if min_value is not None:
            key = 'gte' if include_min else 'gt'
            range_clause[key] = min_value
        
        if max_value is not None:
            key = 'lte' if include_max else 'lt'
            range_clause[key] = max_value
        
        return {'range': {field_name: range_clause}}
    
    @staticmethod
    def create_exists_filter(field_name: str) -> Dict[str, Any]:
        """
        필드 존재 필터 생성
        
        Args:
            field_name: 존재를 확인할 필드명
            
        Returns:
            Dict: Elasticsearch exists 필터
        """
        return {'exists': {'field': field_name}}
    
    @staticmethod
    def combine_filters(
        filters: List[Dict[str, Any]],
        operator: str = "should",
        minimum_should_match: int = 1
    ) -> Dict[str, Any]:
        """
        여러 필터를 조합
        
        Args:
            filters: 조합할 필터들
            operator: 조합 방식 ("must", "should", "must_not")
            minimum_should_match: should일 때 최소 매치 수
            
        Returns:
            Dict: 조합된 bool 필터
        """
        if not filters:
            return {}
        
        if len(filters) == 1:
            return filters[0]
        
        bool_query = {
            "bool": {
                operator: filters
            }
        }
        
        if operator == "should" and minimum_should_match > 0:
            bool_query["bool"]["minimum_should_match"] = minimum_should_match
        
        return bool_query