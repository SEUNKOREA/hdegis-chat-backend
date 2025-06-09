"""
검색 파이프라인 모듈
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from app.core.search.base_searcher import BaseSearcher
from app.core.embedding.base_embedder import BaseEmbedder
from app.utils.input_processor import InputProcessor
from app.utils.query_enhancer import QueryEnhancer
from app.utils.filter_builder import FilterBuilder
from app.config.base_config import SearchConfig
from app.config.model_mappings import auto_configure_for_index

logger = logging.getLogger(__name__)


class Retriever:
    """검색 기능을 담당하는 클래스"""
    
    def __init__(
        self,
        searcher: BaseSearcher,
        embedder: Optional[BaseEmbedder] = None,
        query_enhancer: Optional[QueryEnhancer] = None,
        input_processor: Optional[InputProcessor] = None,
        config: SearchConfig = None
    ):
        """
        검색기 초기화
        
        Args:
            searcher: 검색 엔진
            embedder: 임베딩 모델 (벡터 검색시 필요)
            query_enhancer: 쿼리 향상기 (키워드/HyDE 생성시 필요)
            input_processor: 입력 처리기
            config: 검색 설정
        """
        self.searcher = searcher
        self.embedder = embedder
        self.query_enhancer = query_enhancer
        self.input_processor = input_processor or InputProcessor()
        self.config = config or SearchConfig()
        
        logger.info("검색기 초기화 완료")
    
    def search(
        self,
        user_query: str,
        user_filter: str = "",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        통합 검색 메서드 (config 기반)
        
        Args:
            user_query: 사용자 쿼리
            user_filter: 사용자 필터
            **kwargs: 설정 오버라이드 옵션
            
        Returns:
            List[Dict]: 검색 결과
        """
        # config에서 설정 가져오기 (kwargs로 오버라이드 가능)
        index_name = kwargs.get("index_name", self.config.index_name)
        search_method = kwargs.get("search_method", self.config.search_method)
        top_k = kwargs.get("top_k", self.config.top_k)
        
        try:
            # 인덱스 기반 자동 설정
            search_config = auto_configure_for_index(index_name, search_method, **kwargs)
            
            # 필터 생성
            filters = self._create_filters(user_filter)
            
            # 검색 방법에 따른 분기
            if search_method == "keyword":
                return self._keyword_search(
                    index_name, user_query, filters, top_k, search_config
                )
            elif search_method == "vector":
                return self._vector_search(
                    index_name, user_query, filters, top_k, search_config
                )
            elif search_method == "hybrid":
                return self._hybrid_search(
                    index_name, user_query, filters, top_k, search_config
                )
            elif search_method == "hyde":
                return self._hyde_vector_search(
                    index_name, user_query, filters, top_k, search_config
                )
            elif search_method == "hyde_hybrid":
                return self._hyde_hybrid_search(
                    index_name, user_query, filters, top_k, search_config
                )
            else:
                raise ValueError(f"지원하지 않는 검색 방법: {search_method}")
                
        except Exception as e:
            logger.error(f"검색 실패 ({search_method}): {e}")
            raise
    
    def expand_results(
        self,
        hits: List[Dict[str, Any]],
        tolerance: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        검색 결과를 페이지 단위로 확장
        
        Args:
            hits: 원본 검색 결과
            tolerance: 확장할 페이지 범위 (None이면 config 사용)
            
        Returns:
            Tuple: (확장된 결과, 전체 결과)
        """
        tolerance = tolerance or self.config.tolerance
        
        # tolerance가 0이면 확장하지 않음
        if tolerance == 0:
            logger.info("페이지 확장 비활성화 (tolerance=0)")
            return [], hits
        
        try:
            expanded_hits = self.searcher.expand_search_results(
                self.config.index_name, hits, tolerance
            )
            
            # 원본 + 확장된 결과를 순서대로 조합
            total_hits = self._combine_original_and_expanded(hits, expanded_hits)
            
            logger.info(f"결과 확장: {len(hits)} -> {len(total_hits)} (tolerance={tolerance})")
            return expanded_hits, total_hits
            
        except Exception as e:
            logger.error(f"결과 확장 실패: {e}")
            return [], hits
    
    def _keyword_search(
        self,
        index_name: str,
        user_query: str,
        filters: List[Dict[str, Any]],
        top_k: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """키워드 검색 구현"""
        # 쿼리 향상 (키워드 생성)
        if self.query_enhancer:
            keywords = self.query_enhancer.generate_keywords(user_query)
            # OR로 분리된 키워드들을 공백으로 연결
            keyword_list = [kw.strip() for kw in keywords.split(" OR ")]
            query = " ".join(keyword_list)
            logger.debug(f"생성된 키워드: {keyword_list}")
        else:
            # 번역만 수행
            query = self.input_processor.translate_text(user_query, 'en')
        
        return self.searcher.keyword_search(
            index_name=index_name,
            query=query,
            text_fields=config["text_fields"],
            top_k=top_k,
            filters=filters
        )
    
    def _vector_search(
        self,
        index_name: str,
        user_query: str,
        filters: List[Dict[str, Any]],
        top_k: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """벡터 검색 구현"""
        if not self.embedder:
            raise ValueError("벡터 검색을 위해서는 embedder가 필요합니다")
        
        # 쿼리 임베딩 생성
        if self.embedder.need_translation:
            query_text = self.input_processor.translate_text(user_query, 'en')
        else:
            query_text = user_query
        
        query_vector = self.embedder.embed_text(query_text, task="RETRIEVAL_QUERY")
        logger.debug("쿼리 벡터 생성 완료")
        
        return self.searcher.vector_search(
            index_name=index_name,
            query_vector=query_vector,
            vector_field=config["vector_field"],
            top_k=top_k,
            filters=filters
        )
    
    def _hybrid_search(
        self,
        index_name: str,
        user_query: str,
        filters: List[Dict[str, Any]],
        top_k: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 구현"""
        if not self.embedder:
            raise ValueError("하이브리드 검색을 위해서는 embedder가 필요합니다")
        
        # 쿼리 준비
        translated_query = self.input_processor.translate_text(user_query, 'en')
        
        # 키워드 생성
        if self.query_enhancer:
            keywords = self.query_enhancer.generate_keywords(translated_query, False)
            keyword_list = [kw.strip() for kw in keywords.split(" OR ")]
            text_query = " ".join(keyword_list)
        else:
            text_query = translated_query
        
        # 벡터 생성
        if self.embedder.need_translation:
            query_vector = self.embedder.embed_text(translated_query, task="RETRIEVAL_QUERY")
        else:
            query_vector = self.embedder.embed_text(user_query, task="RETRIEVAL_QUERY")
        
        logger.debug("하이브리드 검색 준비 완료")
        
        return self.searcher.hybrid_search(
            index_name=index_name,
            query=text_query,
            query_vector=query_vector,
            text_fields=config["text_fields"],
            vector_field=config["vector_field"],
            top_k=top_k,
            vector_weight=self.config.vector_weight,
            text_weight=self.config.text_weight,
            filters=filters
        )
    
    def _hyde_vector_search(
        self,
        index_name: str,
        user_query: str,
        filters: List[Dict[str, Any]],
        top_k: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """HyDE 벡터 검색 구현"""
        if not self.embedder or not self.query_enhancer:
            raise ValueError("HyDE 검색을 위해서는 embedder와 query_enhancer가 필요합니다")
        
        # HyDE 문서 생성
        hyde_doc = self.query_enhancer.generate_hyde_document(user_query)
        logger.debug("HyDE 문서 생성 완료")
        
        # HyDE 문서 임베딩
        query_vector = self.embedder.embed_text(hyde_doc, task="RETRIEVAL_QUERY")
        
        return self.searcher.vector_search(
            index_name=index_name,
            query_vector=query_vector,
            vector_field=config["vector_field"],
            top_k=top_k,
            filters=filters
        )
    
    def _hyde_hybrid_search(
        self,
        index_name: str,
        user_query: str,
        filters: List[Dict[str, Any]],
        top_k: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """HyDE 하이브리드 검색 구현"""
        if not self.embedder or not self.query_enhancer:
            raise ValueError("HyDE 하이브리드 검색을 위해서는 embedder와 query_enhancer가 필요합니다")
        
        # 쿼리 준비
        translated_query = self.input_processor.translate_text(user_query, 'en')
        
        # HyDE 문서 생성 및 임베딩
        hyde_doc = self.query_enhancer.generate_hyde_document(translated_query, False)
        query_vector = self.embedder.embed_text(hyde_doc, task="RETRIEVAL_QUERY")
        
        # 키워드 생성
        keywords = self.query_enhancer.generate_keywords(translated_query, False)
        keyword_list = [kw.strip() for kw in keywords.split(" OR ")]
        text_query = " ".join(keyword_list)
        
        logger.debug("HyDE 하이브리드 검색 준비 완료")
        
        return self.searcher.hybrid_search(
            index_name=index_name,
            query=text_query,
            query_vector=query_vector,
            text_fields=config["text_fields"],
            vector_field=config["vector_field"],
            top_k=top_k,
            vector_weight=self.config.vector_weight,
            text_weight=self.config.text_weight,
            filters=filters
        )
    
    def _create_filters(self, user_filter: str) -> List[Dict[str, Any]]:
        """사용자 필터를 Elasticsearch 필터로 변환"""
        if not user_filter or not user_filter.strip():
            return []
        
        return FilterBuilder.create_folder_filters(user_filter)
    
    def _combine_original_and_expanded(
        self,
        original_hits: List[Dict[str, Any]],
        expanded_hits: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """원본과 확장된 결과를 적절한 순서로 조합"""
        # 페이지별로 그룹화하여 순서대로 조합하는 로직
        # 현재는 간단하게 원본 + 확장된 결과 순서로 반환
        total_hits = []
        
        # 원본 결과들을 먼저 추가
        for hit in original_hits:
            total_hits.append(hit)
        
        # 확장된 결과들을 추가
        for hit in expanded_hits:
            total_hits.append(hit)
        
        return total_hits