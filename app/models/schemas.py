# ========================================
# 3. app/models/schemas.py (새로 생성)
# ========================================
"""
Pydantic 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """채팅 요청 스키마"""
    query: str = Field(..., description="사용자 질문", min_length=1, max_length=2000)
    filters: List[str] = Field(default=[], description="문서 필터 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "고압차단기의 동작 원리는 무엇인가요?",
                "filters": [
                    "1. International Standards/IEC",
                    "3. Customer Standard Specifications/Spain/REE"
                ]
            }
        }


class SearchResult(BaseModel):
    """검색 결과 스키마"""
    fileName: str = Field(..., description="파일명")
    filePath: str = Field(..., description="파일 경로 (MinIO URL)")
    pageNumber: int = Field(..., description="페이지 번호")
    score: float = Field(..., description="유사도 점수", ge=0, le=1)
    preview: str = Field(..., description="내용 미리보기")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fileName": "IEC_62271_100.pdf",
                "filePath": "/documents/IEC_62271_100.pdf",
                "pageNumber": 25,
                "score": 0.92,
                "preview": "고압차단기는 전력 시스템에서 회로를 개폐하는 중요한 장비입니다..."
            }
        }


class ChatResponse(BaseModel):
    """채팅 응답 스키마"""
    message: str = Field(..., description="AI 응답 메시지")
    searchResults: List[SearchResult] = Field(..., description="검색 결과 목록")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "고압차단기는 전력 시스템에서 중요한 역할을 합니다...",
                "searchResults": [
                    {
                        "fileName": "IEC_62271_100.pdf",
                        "filePath": "/documents/IEC_62271_100.pdf",
                        "pageNumber": 25,
                        "score": 0.92,
                        "preview": "고압차단기는 전력 시스템에서 회로를 개폐하는..."
                    }
                ],
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class StreamEvent(BaseModel):
    """스트리밍 이벤트 스키마"""
    type: str = Field(..., description="이벤트 타입")
    data: Optional[Dict[str, Any]] = Field(None, description="이벤트 데이터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "response_chunk",
                "data": {"chunk": "고압차단기는"}
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")