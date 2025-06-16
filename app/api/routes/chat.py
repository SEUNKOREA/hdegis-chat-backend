# ========================================
# 8. app/api/routes/chat.py (새로 생성)
# ========================================
"""
채팅 관련 API 엔드포인트
"""

import json
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ChatRequest, 
    ChatResponse, 
    SearchResult,
    ErrorResponse
)
from app.services.chat_service import ChatService
from app.api.dependencies import ChatServiceDep

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="일반 채팅",
    description="사용자 질문에 대한 일반 응답(non-streaming)을 반환 (실제 서비스에서는 미사용, 테스트용)",
    responses={
        200: {"description": "성공적인 응답"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류", "model": ErrorResponse}
    }
)
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = ChatServiceDep
) -> ChatResponse:
    """
    일반 채팅 응답 (non-streaming)
    
    Args:
        request: 채팅 요청 데이터
        chat_service: 채팅 서비스 의존성
        
    Returns:
        채팅 응답
    """
    try:
        logger.info(f"채팅 요청: {request.query[:50]}...")
        
        # 검색 결과 및 응답 생성        
        response_message, search_results = await chat_service.generate_response(
            request.query,
            request.filters
        )
        
        response = ChatResponse(
            message=response_message,
            searchResults=search_results
        )
        
        logger.info("채팅 응답 완료")
        return response
        
    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/chat/stream",
    summary="스트리밍 채팅",
    description="사용자 질문에 대한 스트리밍 응답을 반환합니다.",
    responses={
        200: {
            "description": "스트리밍 응답", 
            "content": {"text/event-stream": {"example": "data: {...}\n\n"}}
        },
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"}
    }
)
async def chat_stream_endpoint(
    request: ChatRequest,
    chat_service: ChatService = ChatServiceDep
):
    """
    스트리밍 채팅 응답
    
    Args:
        request: 채팅 요청 데이터
        chat_service: 채팅 서비스 의존성
        
    Returns:
        Server-Sent Events 스트림
    """
    try:
        logger.info(f"스트리밍 채팅 요청: {request.query[:50]}...")
        
        async def event_stream():
            """SSE 이벤트 스트림 생성기"""
            try:
                async for event in chat_service.generate_streaming_response(
                    request.query, 
                    request.filters
                ):
                    # SSE 형식으로 데이터 전송
                    event_data = event.model_dump()
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                logger.error(f"스트리밍 중 오류: {e}")
                error_event = {
                    "type": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # nginx 버퍼링 비활성화
            }
        )
        
    except Exception as e:
        logger.error(f"스트리밍 설정 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"스트리밍 설정 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/search",
    response_model=List[SearchResult],
    summary="검색만 수행 (실제 서비스에서는 미사용, 테스트용)",
    description="사용자 질문에 대한 검색 결과만 반환합니다."
)
async def search_endpoint(
    request: ChatRequest,
    chat_service: ChatService = ChatServiceDep
) -> List[SearchResult]:
    """
    검색만 수행하는 엔드포인트
    
    Args:
        query: 검색 쿼리
        filters: 문서 필터 목록
        chat_service: 채팅 서비스 의존성
        
    Returns:
        검색 결과 목록
    """
    try:
        logger.info(f"검색 요청: {request.query[:50]}...")
        
        search_results = await chat_service.get_search_results(request.query, request.filters)
        
        logger.info(f"검색 완료: {len(search_results)}개 결과")
        return search_results
        
    except Exception as e:
        logger.error(f"검색 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )
