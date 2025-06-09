"""
스토리지 추상화 인터페이스
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
import os


class BaseStorage(ABC):
    """스토리지 시스템의 추상 인터페이스"""
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        원격 파일을 로컬 경로로 다운로드
        
        Args:
            remote_path: 원격 파일 경로
            local_path: 로컬 저장 경로
            
        Returns:
            bool: 다운로드 성공 여부
        """
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        원격 파일 존재 여부 확인
        
        Args:
            remote_path: 원격 파일 경로
            
        Returns:
            bool: 파일 존재 여부
        """
        pass
    
    @abstractmethod
    def get_file_bytes(self, remote_path: str) -> Optional[bytes]:
        """
        원격 파일 내용을 바이트로 반환
        
        Args:
            remote_path: 원격 파일 경로
            
        Returns:
            bytes: 파일 내용 또는 None
        """
        pass
    
    def ensure_local_dir(self, local_path: str) -> None:
        """로컬 디렉토리가 존재하지 않으면 생성"""
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
    
    def cleanup_local_file(self, local_path: str) -> None:
        """로컬 임시 파일 정리"""
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass  # 파일 삭제 실패해도 무시