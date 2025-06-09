"""
컨텍스트 구성 파이프라인 모듈
"""

from typing import List, Dict, Any
import logging
import os
from google.genai import types

from app.core.storage.base_storage import BaseStorage
from app.config.base_config import ContextConfig

logger = logging.getLogger(__name__)


class ContextBuilder:
    """검색 결과로부터 컨텍스트를 구성하는 클래스"""
    
    def __init__(
        self,
        storage: BaseStorage = None,
        config: ContextConfig = None
    ):
        """
        컨텍스트 빌더 초기화
        
        Args:
            storage: 스토리지 시스템 (이미지 컨텍스트 사용시 필요)
            config: 컨텍스트 설정
        """
        self.storage = storage
        self.config = config or ContextConfig()
        
        # 이미지 컨텍스트 사용시 스토리지 필수
        if self.config.context_type in ("image", "both") and not storage:
            raise ValueError("이미지 컨텍스트를 사용하려면 storage가 필요합니다")
        
        logger.info(f"컨텍스트 빌더 초기화: {self.config.context_type} 타입")
    
    def build_context(self, hits: List[Dict[str, Any]]) -> List[types.Part]:
        """
        검색 결과로부터 컨텍스트 파트들을 생성
        
        Args:
            hits: 검색 결과 리스트
            
        Returns:
            List[types.Part]: 컨텍스트 파트들
        """
        if not hits:
            logger.warning("검색 결과가 없어서 빈 컨텍스트 반환")
            return []
        
        try:
            parts = []
            
            for i, hit in enumerate(hits):
                src = hit.get("_source", {})
                
                # 텍스트 컨텍스트 추가
                if self.config.context_type in ("text", "both"):
                    text_part = self._create_text_part(src, i)
                    if text_part:
                        parts.append(text_part)
                
                # 이미지 컨텍스트 추가
                if self.config.context_type in ("image", "both"):
                    image_part = self._create_image_part(src, i)
                    if image_part:
                        parts.append(image_part)
            
            logger.info(f"컨텍스트 구성 완료: {len(parts)}개 파트")
            return parts
            
        except Exception as e:
            logger.error(f"컨텍스트 구성 실패: {e}")
            return []
    
    def _create_text_part(self, source: Dict[str, Any], index: int) -> types.Part:
        """텍스트 파트 생성"""
        try:
            # 설정된 텍스트 필드에서 내용 추출
            text_content = source.get(self.config.text_field, "")
            
            if not text_content:
                # fallback 필드들 시도
                fallback_fields = ["content", "extracted_text", "text"]
                for field in fallback_fields:
                    text_content = source.get(field, "")
                    if text_content:
                        break
            
            if not text_content:
                logger.warning(f"텍스트 내용을 찾을 수 없음 (index: {index})")
                return None
            
            # 메타데이터 포함한 텍스트 구성
            metadata = self._extract_metadata(source)
            if metadata:
                formatted_text = f"[Document {index + 1}]\n{metadata}\n\n{text_content}"
            else:
                formatted_text = f"[Document {index + 1}]\n{text_content}"
            
            return types.Part.from_text(text=formatted_text)
            
        except Exception as e:
            logger.error(f"텍스트 파트 생성 실패 (index: {index}): {e}")
            return None
    
    def _create_image_part(self, source: Dict[str, Any], index: int) -> types.Part:
        """이미지 파트 생성"""
        if not self.storage:
            logger.error("스토리지가 설정되지 않아 이미지 파트 생성 불가")
            return None
        
        try:
            # 이미지 경로 추출
            image_path = source.get("minio_image_path") or source.get("image_path")
            if not image_path:
                logger.warning(f"이미지 경로를 찾을 수 없음 (index: {index})")
                return None
            
            # 로컬 임시 경로 생성
            local_path = os.path.join(
                self.config.context_type == "both" and "tmp" or "tmp",
                f"context_image_{index}_{os.path.basename(image_path)}"
            )
            
            # 이미지 다운로드
            if not self.storage.download_file(image_path, local_path):
                logger.error(f"이미지 다운로드 실패: {image_path}")
                return None
            
            # 이미지 바이트 읽기
            try:
                with open(local_path, "rb") as f:
                    image_bytes = f.read()
                
                # 임시 파일 정리
                self.storage.cleanup_local_file(local_path)
                
                return types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/png"  # 기본적으로 PNG로 처리
                )
                
            except Exception as e:
                logger.error(f"이미지 파일 읽기 실패: {e}")
                self.storage.cleanup_local_file(local_path)
                return None
            
        except Exception as e:
            logger.error(f"이미지 파트 생성 실패 (index: {index}): {e}")
            return None
    
    def _extract_metadata(self, source: Dict[str, Any]) -> str:
        """문서 메타데이터 추출"""
        metadata_parts = []
        
        # 경로 정보
        if "gcs_pdf_path" in source:
            metadata_parts.append(f"Source: {source['gcs_pdf_path']}")
        elif "pdf_name" in source:
            metadata_parts.append(f"File: {source['pdf_name']}")
        
        # 페이지 정보
        if "page_number" in source:
            metadata_parts.append(f"Page: {source['page_number']}")
        elif "page" in source:
            metadata_parts.append(f"Page: {source['page']}")
        
        # 폴더 정보
        if "folder_levels" in source and source["folder_levels"]:
            folder_path = "/".join(source["folder_levels"])
            metadata_parts.append(f"Path: {folder_path}")
        
        return "\n".join(metadata_parts) if metadata_parts else ""