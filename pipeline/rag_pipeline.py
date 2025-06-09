"""
통합 RAG 파이프라인
"""

from typing import List, Dict, Any, Tuple, Optional, Generator, Iterator
import logging

from pipeline.retriever import Retriever
from pipeline.context_builder import ContextBuilder
from pipeline.generator import Generator
from utils.formatters import timed

logger = logging.getLogger(__name__)


class RAGPipeline:
    """통합 RAG 파이프라인 클래스"""
    
    def __init__(
        self,
        retriever: Retriever,
        context_builder: ContextBuilder,
        generator: Generator
    ):
        """
        RAG 파이프라인 초기화
        
        Args:
            retriever: 검색기 (config 포함)
            context_builder: 컨텍스트 빌더
            generator: 답변 생성기
        """
        self.retriever = retriever
        self.context_builder = context_builder
        self.generator = generator
        
        logger.info(f"RAG 파이프라인 초기화 완료: {retriever.config.search_method} 방식, {retriever.config.index_name} 인덱스")
    
    def run(
        self,
        user_query: str,
        user_filter: str = ""
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        전체 RAG 파이프라인 실행 (동적 데이터만 받음)
        
        Args:
            user_query: 사용자 질문 (동적)
            user_filter: 사용자 필터 (동적)
            
        Returns:
            Tuple: (생성된 답변, 전체 컨텍스트 hits, 원본 검색 hits)
        """
        logger.info(f"RAG 파이프라인 시작: '{user_query[:50]}...'")
        
        try:
            # 1. 검색 (config 기반)
            hits = timed(
                "검색",
                self.retriever.search,
                user_query=user_query,
                user_filter=user_filter
            )
            
            if not hits:
                logger.warning("검색 결과가 없습니다")
                return "검색 결과를 찾을 수 없습니다.", [], []
            
            # 2. 결과 확장 (config의 tolerance 설정에 따라)
            total_hits = hits
            if self.retriever.config.tolerance > 0:
                expanded_hits, total_hits = timed(
                    "결과 확장",
                    self.retriever.expand_results,
                    hits
                )
            
            # 3. 컨텍스트 구성
            context_parts = timed(
                "컨텍스트 구성",
                self.context_builder.build_context,
                total_hits
            )
            
            # 4. 답변 생성
            answer = timed(
                "답변 생성",
                self.generator.generate_answer,
                user_query,
                context_parts
            )
            
            logger.info("RAG 파이프라인 완료")
            return answer, total_hits, hits
            
        except Exception as e:
            logger.error(f"RAG 파이프라인 실행 실패: {e}")
            return f"처리 중 오류가 발생했습니다: {str(e)}", [], []
    
    def search_only(
        self,
        user_query: str,
        user_filter: str = ""
    ) -> List[Dict[str, Any]]:
        """
        검색만 수행 (답변 생성 없이)
        
        Args:
            user_query: 사용자 질문
            user_filter: 사용자 필터
            
        Returns:
            List[Dict]: 검색 결과
        """
        return self.retriever.search(
            user_query=user_query,
            user_filter=user_filter
        )
    
    def generate_only(
        self,
        user_query: str,
        hits: List[Dict[str, Any]],
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        기존 검색 결과로 답변만 생성
        
        Args:
            user_query: 사용자 질문
            hits: 검색 결과
            generation_config: 생성 설정
            
        Returns:
            str: 생성된 답변
        """
        try:
            # 컨텍스트 구성
            context_parts = self.context_builder.build_context(hits)
            
            # 답변 생성
            return self.generator.generate_answer(
                user_query,
                context_parts,
                generation_config
            )
            
        except Exception as e:
            logger.error(f"답변 생성 실패: {e}")
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    def run_stream(
        self,
        user_query: str,
        user_filter: str = ""
    ) -> Tuple[Iterator[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        스트리밍 RAG 파이프라인 실행 (검색 결과도 함께 반환)
        
        Args:
            user_query: 사용자 질문 (동적)
            user_filter: 사용자 필터 (동적)
            
        Returns:
            Tuple: (답변 스트림 이터레이터, 전체 컨텍스트 hits, 원본 검색 hits)
        """
        logger.info(f"스트리밍 RAG 파이프라인 시작: '{user_query[:50]}...'")
        
        try:
            # 1. 검색 (config 기반)
            hits = timed(
                "검색",
                self.retriever.search,
                user_query=user_query,
                user_filter=user_filter
            )
            
            if not hits:
                logger.warning("검색 결과가 없습니다")
                def empty_generator():
                    yield "검색 결과를 찾을 수 없습니다."
                return empty_generator(), [], []
            
            # 2. 결과 확장 (config의 tolerance 설정에 따라)
            total_hits = hits
            if self.retriever.config.tolerance > 0:
                expanded_hits, total_hits = timed(
                    "결과 확장",
                    self.retriever.expand_results,
                    hits
                )
            
            # 3. 컨텍스트 구성
            context_parts = timed(
                "컨텍스트 구성",
                self.context_builder.build_context,
                total_hits
            )
            
            # 4. 스트리밍 답변 생성
            logger.info("스트리밍 답변 생성 시작")
            
            def answer_generator():
                for chunk in self.generator.generate_answer_stream(
                    user_query,
                    context_parts
                ):
                    yield chunk
                logger.info("스트리밍 RAG 파이프라인 완료")
            
            return answer_generator(), total_hits, hits
            
        except Exception as e:
            logger.error(f"스트리밍 RAG 파이프라인 실행 실패: {e}")
            def error_generator():
                yield f"처리 중 오류가 발생했습니다: {str(e)}"
            return error_generator(), [], []
    
    def generate_only_stream(
        self,
        user_query: str,
        hits: List[Dict[str, Any]],
        generation_config: Optional[Dict[str, Any]] = None
    ) -> Iterator[str]:
        """
        기존 검색 결과로 스트리밍 답변만 생성
        
        Args:
            user_query: 사용자 질문
            hits: 검색 결과
            generation_config: 생성 설정
            
        Yields:
            str: 생성된 답변 청크
        """
        try:
            # 컨텍스트 구성
            context_parts = self.context_builder.build_context(hits)
            
            # 스트리밍 답변 생성
            for chunk in self.generator.generate_answer_stream(
                user_query,
                context_parts,
                generation_config
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"스트리밍 답변 생성 실패: {e}")
            yield f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    # 설정 조회 메서드들 (디버깅용)
    def get_config(self) -> Dict[str, Any]:
        """현재 파이프라인 설정 반환"""
        return {
            "search_config": {
                "index_name": self.retriever.config.index_name,
                "search_method": self.retriever.config.search_method,
                "top_k": self.retriever.config.top_k,
                "tolerance": self.retriever.config.tolerance,
                "vector_weight": self.retriever.config.vector_weight,
                "text_weight": self.retriever.config.text_weight
            }
        }
    
    def update_search_config(self, **kwargs):
        """검색 설정 업데이트 (필요시)"""
        for key, value in kwargs.items():
            if hasattr(self.retriever.config, key):
                setattr(self.retriever.config, key, value)
                logger.info(f"검색 설정 업데이트: {key} = {value}")
            else:
                logger.warning(f"알 수 없는 검색 설정: {key}")