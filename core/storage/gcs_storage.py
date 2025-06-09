"""
Google Cloud Storage 구현 (추후 구현)
"""

from typing import Optional
import logging
from google.cloud import storage
from google.cloud.exceptions import NotFound

from .base_storage import BaseStorage
from config.secrets_config import GoogleCloudSecrets

logger = logging.getLogger(__name__)


class GCSStorage(BaseStorage):
    """Google Cloud Storage 구현"""
    
    def __init__(self, secrets: GoogleCloudSecrets, bucket_name: str):
        """
        GCS 클라이언트 초기화
        
        Args:
            secrets: Google Cloud 인증 정보
            bucket_name: 버킷명
        """
        self.bucket_name = bucket_name
        self.client = storage.Client(project=secrets.project_id)
        self.bucket = self.client.bucket(bucket_name)
        
        # 연결 테스트
        try:
            self.bucket.exists()
            logger.info(f"GCS 연결 성공: {secrets.project_id}/{bucket_name}")
        except Exception as e:
            logger.error(f"GCS 연결 실패: {e}")
            raise
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """GCS에서 파일 다운로드"""
        try:
            self.ensure_local_dir(local_path)
            blob = self.bucket.blob(remote_path)
            blob.download_to_filename(local_path)
            logger.debug(f"파일 다운로드 성공: {remote_path} -> {local_path}")
            return True
            
        except NotFound:
            logger.error(f"파일을 찾을 수 없음: {remote_path}")
            return False
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {remote_path} - {e}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """GCS에서 파일 존재 여부 확인"""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False
    
    def get_file_bytes(self, remote_path: str) -> Optional[bytes]:
        """GCS에서 파일 내용을 바이트로 반환"""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.download_as_bytes()
            
        except NotFound:
            logger.error(f"파일을 찾을 수 없음: {remote_path}")
            return None
        except Exception as e:
            logger.error(f"파일 읽기 실패: {remote_path} - {e}")
            return None