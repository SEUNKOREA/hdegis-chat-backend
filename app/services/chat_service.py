# ========================================
# 4. app/services/chat_service.py (새로 생성)
# ========================================
"""
채팅 서비스 비즈니스 로직
"""

import json
import asyncio
from typing import List, AsyncGenerator, Optional
import logging

from app.models.schemas import SearchResult, StreamEvent
from app.factories import RAGPipelineFactory

logger = logging.getLogger(__name__)


class ChatService:
    """채팅 서비스 클래스"""
    
    def __init__(self):
        """채팅 서비스 초기화"""
        try:
            self.pipeline = RAGPipelineFactory.create_pipeline()
            logger.info("RAG 파이프라인 초기화 완료")
        except Exception as e:
            logger.error(f"RAG 파이프라인 초기화 실패: {e}")
            raise
    
    async def get_search_results(self, query: str, filters: List[str]) -> List[SearchResult]:
        """
        검색 결과만 반환
        
        Args:
            query: 사용자 질문
            filters: 문서 필터 목록
            
        Returns:
            검색 결과 목록
        """
        try:
            # 필터 문자열 생성
            filter_str = " & ".join(filters) if filters else ""
            
            # 검색 실행 (동기 함수를 비동기로 실행)
            loop = asyncio.get_event_loop()
            hits = await loop.run_in_executor(
                None, 
                self.pipeline.search_only, 
                query, 
                filter_str
            )
            
            # 검색 결과 포맷팅
            return self._format_search_results(hits)
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            raise
    
    async def generate_response(self, query: str, filters: List[str]) -> str:
        """
        일반 응답 생성 (non-streaming)
        
        Args:
            query: 사용자 질문
            filters: 문서 필터 목록
            
        Returns:
            AI 응답
        """
        try:
            filter_str = " & ".join(filters) if filters else ""
            
            # 응답 생성 (동기 함수를 비동기로 실행)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.pipeline.run,
                query,
                filter_str
            )
            
            answer, total_hits, original_hits = result
            return answer
            
        except Exception as e:
            logger.error(f"응답 생성 실패: {e}")
            raise
    
    async def generate_streaming_response(
        self, 
        query: str, 
        filters: List[str]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        스트리밍 응답 생성
        
        Args:
            query: 사용자 질문
            filters: 문서 필터 목록
            
        Yields:
            스트리밍 이벤트
        """
        try:
            # 1. 먼저 검색 결과 전송
            search_results = await self.get_search_results(query, filters)
            yield StreamEvent(
                type="search_results",
                data={"searchResults": [result.model_dump() for result in search_results]}
            )
            
            # 2. 스트리밍 응답 생성 및 전송
            filter_str = " & ".join(filters) if filters else ""
            
            # 동기 제너레이터를 비동기로 변환
            loop = asyncio.get_event_loop()
            
            def get_stream_generator():
                return self.pipeline.run_stream(query, filter_str)
            
            # 스트림 생성기를 별도 스레드에서 실행
            stream_gen = await loop.run_in_executor(None, get_stream_generator)
            
            # 청크별로 전송
            for chunk in stream_gen:
                if chunk:  # 빈 청크 제외
                    yield StreamEvent(
                        type="response_chunk",
                        data={"chunk": chunk}
                    )
                    # 비동기 컨텍스트에서 다른 작업이 실행될 수 있도록 양보
                    await asyncio.sleep(0)
            
            # 3. 완료 신호
            yield StreamEvent(type="completed", data={})
            
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 실패: {e}")
            yield StreamEvent(
                type="error",
                data={"error": str(e)}
            )
    
    def _format_search_results(self, hits: List) -> List[SearchResult]:
        """
        검색 결과를 API 응답 형식으로 변환
        
        Args:
            hits: Elasticsearch 검색 결과
            
        Returns:
            포맷팅된 검색 결과
        """
        results = []
        
        for hit in hits:
            try:
                src = hit.get("_source", {})
                
                # 파일 경로 처리 (MinIO 경로 또는 로컬 경로)
                file_path = src.get("minio_pdf_path") or src.get("gcs_pdf_path") or "public/sample.pdf"
                
                # 미리보기 텍스트 생성
                preview_text = src.get("extracted_text") or src.get("content") or ""
                preview = (preview_text[:200] + "...") if len(preview_text) > 200 else preview_text
                
                result = SearchResult(
                    fileName=src.get("pdf_name") or "Unknown",
                    filePath=file_path,
                    pageNumber=int(src.get("page_number") or src.get("page") or 0),
                    score=float(hit.get("_score", 0)),
                    preview=preview
                )
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"검색 결과 포맷팅 실패: {e}")
                continue
        
        return results