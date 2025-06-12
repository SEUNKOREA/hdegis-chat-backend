# ========================================
# 4. app/services/chat_service.py (개선된 버전)
# ========================================
"""
채팅 서비스 비즈니스 로직 - 스트리밍 개선 버전
"""
import os
import json
import asyncio
from typing import List, AsyncGenerator, Optional, Tuple
import logging

from app.models.schemas import SearchResult, StreamEvent
from app.factories import RAGPipelineFactory
from app.config.pipeline_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class ChatService:
    """채팅 서비스 클래스"""
    
    def __init__(self, pipeline_config=None):
        """
        채팅 서비스 초기화
        
        Args:
            pipeline_config: 파이프라인 설정 (None이면 기본 설정 사용)
        """
        try:
            # 설정이 제공되지 않으면 기본 설정 사용
            if pipeline_config is None:
                pipeline_config = DEFAULT_CONFIG

            self.pipeline = RAGPipelineFactory.create_pipeline(config=pipeline_config)
            self.current_config = pipeline_config   # 현재설정 보관
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
    
    async def generate_response(self, query: str, filters: List[str]) -> Tuple:
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
            return answer, self._format_search_results(original_hits)
            
        except Exception as e:
            logger.error(f"응답 생성 실패: {e}")
            raise
    
    async def generate_streaming_response(
        self, 
        query: str, 
        filters: List[str]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        스트리밍 응답 생성 (개선된 버전)
        
        Args:
            query: 사용자 질문
            filters: 문서 필터 목록
            
        Yields:
            스트리밍 이벤트
        """
        try:
            filter_str = " & ".join(filters) if filters else ""
            
            # 1단계: 스트리밍 파이프라인 실행 (검색 + 답변 생성)
            logger.info("스트리밍 파이프라인 시작")
            
            # 검색과 답변 생성을 별도 스레드에서 실행
            loop = asyncio.get_event_loop()
            
            # 검색 결과를 미리 가져오기 (답변 완료 후 전송용)
            search_results_task = loop.run_in_executor(
                None,
                self.get_search_results_sync,
                query,
                filters
            )
            
            # 스트리밍 답변 생성
            stream_task = loop.run_in_executor(
                None,
                self.get_streaming_generator,
                query,
                filter_str
            )
            
            # 스트리밍 답변을 실시간으로 전송
            stream_generator = await stream_task
            
            # 2단계: 답변 스트리밍 (실제 타이핑 효과)
            full_answer = ""
            chunk_buffer = ""
            
            for chunk in stream_generator:
                if chunk:
                    full_answer += chunk
                    chunk_buffer += chunk
                    
                    # 청크를 더 작은 단위로 분할하여 타이핑 효과 구현
                    while len(chunk_buffer) > 0:
                        # 한 번에 1-3글자씩 전송 (자연스러운 타이핑 효과)
                        send_length = min(len(chunk_buffer), 3)
                        send_chunk = chunk_buffer[:send_length]
                        chunk_buffer = chunk_buffer[send_length:]
                        
                        yield StreamEvent(
                            type="response_chunk",
                            data={"chunk": send_chunk}
                        )
                        
                        # 타이핑 속도 조절 (20-50ms 간격)
                        await asyncio.sleep(0.02 + len(send_chunk) * 0.01)
            
            # 3단계: 답변 완료 신호
            yield StreamEvent(type="response_completed", data={})
            logger.info("답변 스트리밍 완료")
            
            # 4단계: 잠시 대기 후 검색 결과 전송 (자연스러운 UX)
            await asyncio.sleep(1.0)  # 1초 대기
            
            # 검색 결과 가져오기
            search_results = await search_results_task
            
            yield StreamEvent(
                type="search_results",
                data={"searchResults": [result.model_dump() for result in search_results]}
            )
            
            # 5단계: 전체 완료 신호
            yield StreamEvent(type="completed", data={})
            logger.info("스트리밍 프로세스 완전 완료")
            
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 실패: {e}")
            yield StreamEvent(
                type="error",
                data={"error": str(e)}
            )
    
    def get_search_results_sync(self, query: str, filters: List[str]) -> List[SearchResult]:
        """
        동기 버전 검색 결과 반환 (스레드 실행용)
        
        Args:
            query: 사용자 질문
            filters: 문서 필터 목록
            
        Returns:
            검색 결과 목록
        """
        try:
            filter_str = " & ".join(filters) if filters else ""
            hits = self.pipeline.search_only(query, filter_str)
            return self._format_search_results(hits)
        except Exception as e:
            logger.error(f"동기 검색 실패: {e}")
            return []
    
    def get_streaming_generator(self, query: str, filter_str: str):
        """
        동기 스트리밍 제너레이터 반환 (스레드 실행용)
        
        Args:
            query: 사용자 질문
            filter_str: 필터 문자열
            
        Returns:
            스트리밍 제너레이터
        """
        try:
            # RAG 파이프라인에서 스트리밍 제너레이터 가져오기
            answer_stream, total_hits, original_hits = self.pipeline.run_stream(query, filter_str)
            return answer_stream
        except Exception as e:
            logger.error(f"스트리밍 제너레이터 생성 실패: {e}")
            # 에러 시 빈 제너레이터 반환
            def empty_generator():
                yield f"답변 생성 중 오류가 발생했습니다: {str(e)}"
            return empty_generator()
    
    async def generate_chunked_response(
        self,
        text: str,
        chunk_size: int = 3,
        delay_ms: int = 0
    ) -> AsyncGenerator[str, None]:
        """
        텍스트를 청크 단위로 분할하여 스트리밍 (타이핑 효과용)
        
        Args:
            text: 전체 텍스트
            chunk_size: 청크 크기 (글자 수)
            delay_ms: 청크 간 지연 시간 (밀리초)
            
        Yields:
            텍스트 청크
        """
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(delay_ms / 1000.0)
    
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
                
                result = SearchResult(
                    fileName=os.path.basename(file_path) or "Unknown",
                    filePath=file_path,
                    pageNumber=int(src.get("page_number") or src.get("page") or 0),
                    score=float(hit.get("_score", -1)),
                )
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"검색 결과 포맷팅 실패: {e}")
                continue
        
        return results